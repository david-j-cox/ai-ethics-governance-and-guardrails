"""Source-monitoring agent.

Weekly job with two independent pipelines:

  A. Source watch (html / link-check sources)
     - Fetch each tracked URL, compare content hash to last run.
     - For changed html sources, ask Claude to summarize and propose surgical
       find/replace edits to affected docs/ pages.
     - For link-check sources, just verify the URL still resolves.
     - On change, opens a "Source updates" PR with applied edits + state.json.

  B. Feed digest (feed sources)
     - Read RSS/Atom feeds, dedupe new entries against state.json by entry ID.
     - Send all new entries (titles + abstracts) in one batched call to Claude
       for relevance triage and a one-line pitch each.
     - Opens a SEPARATE "Research digest" PR whose body is the maintainer-
       facing list of items worth attention. No docs edits.

Both pipelines write to the same agent/state.json but stage their commits on
distinct branches and produce distinct PRs. A clean week produces zero PRs.

Design contract:
  - PR-only, never auto-merges. The maintainer is the human in the loop.
  - Source-watch PRs propose docs edits. Digest PRs are pointers, not edits.
  - Fetch failures are logged and skipped, not fatal.
  - Unchanged sources / no-new-feed-entries trigger zero LLM calls.

Environment:
  - ANTHROPIC_API_KEY: required for any LLM call. Supplied via GH Actions
    repo secret.
  - GITHUB_TOKEN: required for opening PRs. Supplied automatically by Actions.
  - GITHUB_REPOSITORY: "owner/repo". Supplied automatically by Actions; falls
    back to git remote parsing for local dev.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import feedparser
import httpx
import trafilatura
import yaml
from anthropic import Anthropic, APIError

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = Path(__file__).resolve().parent
SOURCES_DIR = AGENT_DIR / "sources"
STATE_PATH = AGENT_DIR / "state.json"
DOCS_ROOT = REPO_ROOT / "docs"
LLMS_TXT_PATH = DOCS_ROOT / "llms.txt"

USER_AGENT = (
    "responsible-clinical-ai-monitor/1.0 "
    "(+https://github.com/david-j-cox/ai-ethics-governance-and-guardrails)"
)
HTTP_TIMEOUT = 30.0
MODEL = "claude-opus-4-7"
MAX_OUTPUT_TOKENS = 16000
SNAPSHOT_BYTES = 8000  # cap stored extracted text in state.json
MAX_FEED_ENTRIES_PER_SOURCE = 30  # cap entries inspected per feed per run
MAX_FEED_ENTRIES_PER_RUN = 150  # cap total entries sent to Claude per run


# =====================================================================
# Source loading
# =====================================================================


@dataclass
class Source:
    id: str
    url: str
    type: str  # "html" | "link-check" | "feed"
    cadence: str
    applies_to: list[str] = field(default_factory=list)
    notes: str = ""


def load_sources() -> list[Source]:
    sources: list[Source] = []
    for path in sorted(SOURCES_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        for entry in data.get("sources", []):
            sources.append(
                Source(
                    id=entry["id"],
                    url=entry["url"],
                    type=entry.get("type", "html"),
                    cadence=entry.get("cadence", "weekly"),
                    applies_to=entry.get("applies_to", []),
                    notes=entry.get("notes", ""),
                )
            )
    return sources


def load_state() -> dict[str, dict]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(state: dict[str, dict]) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# =====================================================================
# Pipeline A: source watch (html / link-check)
# =====================================================================


@dataclass
class FetchResult:
    ok: bool
    content: str = ""
    content_hash: str = ""
    error: str = ""


@dataclass
class SourceChange:
    source: Source
    new_content: str
    new_hash: str
    old_snapshot: str


@dataclass
class ProposedEdit:
    path: str
    rationale: str
    patch_kind: str  # "replace" | "append" | "no-edit"
    find: str = ""
    replace: str = ""


@dataclass
class SourceReport:
    source: Source
    summary: str
    edits: list[ProposedEdit] = field(default_factory=list)
    error: str = ""


def fetch_html(source: Source, client: httpx.Client) -> FetchResult:
    """Fetch html or link-check source. Extract main content for html."""
    try:
        resp = client.get(source.url, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        return FetchResult(ok=False, error=f"fetch error: {e}")

    if source.type == "link-check":
        body = resp.text or ""
        if not body.strip():
            return FetchResult(ok=False, error="empty body")
        return FetchResult(ok=True, content="", content_hash="link-ok")

    extracted = trafilatura.extract(resp.text, include_comments=False, include_tables=True)
    if not extracted:
        return FetchResult(ok=False, error="trafilatura returned no content")
    extracted = extracted.strip()
    return FetchResult(ok=True, content=extracted, content_hash=hash_content(extracted))


def detect_source_changes(
    sources: list[Source],
    state: dict[str, dict],
    client: httpx.Client,
) -> tuple[list[SourceChange], list[tuple[Source, str]], dict[str, dict]]:
    changes: list[SourceChange] = []
    errors: list[tuple[Source, str]] = []
    updated_state = dict(state)
    now = datetime.now(timezone.utc).isoformat()

    for source in sources:
        result = fetch_html(source, client)
        if not result.ok:
            errors.append((source, result.error))
            continue

        prior = state.get(source.id, {})
        prior_hash = prior.get("content_hash", "")

        record = dict(prior)
        record["last_checked"] = now
        record["content_hash"] = result.content_hash
        record["url"] = source.url

        if source.type == "link-check":
            updated_state[source.id] = record
            continue

        if not result.content:
            updated_state[source.id] = record
            continue

        record["snapshot"] = result.content[:SNAPSHOT_BYTES]
        updated_state[source.id] = record

        if prior_hash and prior_hash != result.content_hash:
            changes.append(
                SourceChange(
                    source=source,
                    new_content=result.content,
                    new_hash=result.content_hash,
                    old_snapshot=prior.get("snapshot", ""),
                )
            )

    return changes, errors, updated_state


SOURCE_WATCH_SYSTEM = """You are the source-monitoring agent for the Responsible Clinical AI documentation site (https://david-j-cox.github.io/ai-ethics-governance-and-guardrails/).

Your job: when a tracked external source (regulatory guidance, framework standard, vendor docs, professional-society guideline) changes, propose edits to the site's affected markdown pages so the site stays accurate.

Rules:
1. Be conservative. Many "changes" are cosmetic (footer dates, navigation tweaks, minor wording). If the substantive content the site relies on has not changed, propose no edits and say so.
2. Cite. Every proposed edit must cite what changed in the source and why the site needs to reflect it.
3. Small diffs. Prefer surgical find/replace over wholesale rewrites. The maintainer reviews every PR; small diffs are easier to evaluate.
4. Preserve voice. The site is opinionated, plain English, no em dashes, written for both builders and buyers. Match the existing voice of the page you are editing.
5. Never invent. If the source says X and the site says Y but the relationship is unclear, propose `no-edit` and flag for human review in the rationale.
6. No structural changes. Don't add or remove headings, reorder sections, or restructure pages. Edit prose within existing structure.

For each affected page, return one of:
- A `replace` edit: an exact `find` string from the page and a `replace` string (preserving the surrounding indentation and formatting).
- An `append` edit: a `replace` string to add to the end of the page (e.g., a new bullet under an existing list).
- A `no-edit` decision with rationale, when the source change does not warrant a site change.

You will be given:
- The source ID, URL, and notes.
- A diff summary or content snapshot for the source change.
- The current contents of each affected page.

Return strictly-formatted JSON matching the schema you'll be shown."""


SOURCE_REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "edits": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "path": {"type": "string"},
                    "rationale": {"type": "string"},
                    "patch_kind": {"type": "string", "enum": ["replace", "append", "no-edit"]},
                    "find": {"type": "string"},
                    "replace": {"type": "string"},
                },
                "required": ["path", "rationale", "patch_kind", "find", "replace"],
            },
        },
    },
    "required": ["summary", "edits"],
}


def build_source_user_message(change: SourceChange) -> str:
    parts: list[str] = []
    parts.append("# Source change\n")
    parts.append(f"**ID:** {change.source.id}")
    parts.append(f"**URL:** {change.source.url}")
    parts.append(f"**Notes:** {change.source.notes.strip() or '(none)'}\n")

    if change.old_snapshot:
        parts.append("## Prior snapshot (truncated)\n")
        parts.append("```")
        parts.append(change.old_snapshot[:4000])
        parts.append("```\n")
    else:
        parts.append("## Prior snapshot\n_None, first time this source has been observed._\n")

    parts.append("## Current content (truncated)\n")
    parts.append("```")
    parts.append(change.new_content[:8000])
    parts.append("```\n")

    parts.append("## Affected site pages\n")
    parts.append(
        "These are the pages currently referenced by `applies_to:` in the source's "
        "YAML definition. For each, decide whether the source change requires an edit."
    )
    return "\n".join(parts)


def read_affected_pages(change: SourceChange) -> list[tuple[str, str]]:
    pages: list[tuple[str, str]] = []
    for rel in change.source.applies_to:
        path = DOCS_ROOT / rel
        if not path.exists():
            continue
        pages.append((f"docs/{rel}", path.read_text()))
    return pages


def call_claude_for_source(client: Anthropic, change: SourceChange) -> SourceReport:
    user_blocks: list[dict] = [{"type": "text", "text": build_source_user_message(change)}]
    pages = read_affected_pages(change)
    for path, content in pages:
        user_blocks.append(
            {
                "type": "text",
                "text": f"### `{path}` (current contents)\n\n```markdown\n{content}\n```",
                "cache_control": {"type": "ephemeral"},
            }
        )

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": SOURCE_REPORT_SCHEMA},
            },
            system=[
                {
                    "type": "text",
                    "text": SOURCE_WATCH_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_blocks}],
        ) as stream:
            final = stream.get_final_message()
    except APIError as e:
        return SourceReport(source=change.source, summary="", error=f"Claude API error: {e}")

    text_blocks = [b.text for b in final.content if b.type == "text"]
    if not text_blocks:
        return SourceReport(source=change.source, summary="", error="no text output from model")

    raw = text_blocks[0].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return SourceReport(
            source=change.source,
            summary="",
            error=f"could not parse JSON output: {e}\nraw: {raw[:500]}",
        )

    edits = [
        ProposedEdit(
            path=e["path"],
            rationale=e["rationale"],
            patch_kind=e["patch_kind"],
            find=e.get("find", ""),
            replace=e.get("replace", ""),
        )
        for e in data.get("edits", [])
    ]
    return SourceReport(source=change.source, summary=data["summary"], edits=edits)


def llms_txt_referenced_pages() -> set[str]:
    """Return docs/ paths referenced by llms.txt as canonical site-relative URLs.

    Resolves each https://responsible-clinical-ai.org/<slug>/ link to its
    docs/<slug>.md or docs/<slug>/index.md source file. Used to flag PRs
    that touch curated entry points so the maintainer can revisit llms.txt.
    """
    if not LLMS_TXT_PATH.exists():
        return set()
    import re
    text = LLMS_TXT_PATH.read_text()
    referenced: set[str] = set()
    for url in re.findall(r"https://responsible-clinical-ai\.org/([^\s)]*)", text):
        slug = url.strip("/")
        if not slug:
            candidate = "docs/index.md"
        else:
            md_candidate = DOCS_ROOT / f"{slug}.md"
            index_candidate = DOCS_ROOT / slug / "index.md"
            if md_candidate.exists():
                candidate = f"docs/{slug}.md"
            elif index_candidate.exists():
                candidate = f"docs/{slug}/index.md"
            else:
                continue
        referenced.add(candidate)
    return referenced


def apply_edit(edit: ProposedEdit) -> tuple[bool, str]:
    if edit.patch_kind == "no-edit":
        return False, f"skip {edit.path}: {edit.rationale}"

    path = REPO_ROOT / edit.path
    if not path.exists():
        return False, f"file not found: {edit.path}"

    content = path.read_text()

    if edit.patch_kind == "append":
        new_content = content.rstrip() + "\n\n" + edit.replace.strip() + "\n"
        path.write_text(new_content)
        return True, f"appended to {edit.path}"

    if edit.patch_kind == "replace":
        if not edit.find:
            return False, f"replace edit on {edit.path} had empty 'find'"
        if edit.find not in content:
            return False, f"'find' string not found in {edit.path}"
        if content.count(edit.find) > 1:
            return False, f"'find' string ambiguous in {edit.path} (matches {content.count(edit.find)} times)"
        new_content = content.replace(edit.find, edit.replace, 1)
        path.write_text(new_content)
        return True, f"replaced text in {edit.path}"

    return False, f"unknown patch_kind: {edit.patch_kind}"


# =====================================================================
# Pipeline B: feed digest
# =====================================================================


@dataclass
class FeedEntry:
    source_id: str
    entry_id: str  # stable per-entry identifier (link, GUID, or arXiv id)
    title: str
    summary: str
    link: str
    published: str  # ISO-ish, best-effort


@dataclass
class TriagedEntry:
    entry: FeedEntry
    relevant: bool
    pitch: str  # one-line summary if relevant; "" if not


def feed_entry_id(entry: dict) -> str:
    """Pick a stable id for a feed entry. Prefer 'id', then 'link', then a hash of title+published."""
    candidate = entry.get("id") or entry.get("link") or ""
    if candidate:
        return candidate
    payload = (entry.get("title") or "") + "|" + (entry.get("published") or "")
    return hash_content(payload)[:32]


def fetch_feed(source: Source) -> tuple[list[FeedEntry], str]:
    """Fetch and parse a feed. Returns (entries, error)."""
    try:
        parsed = feedparser.parse(source.url, agent=USER_AGENT)
    except Exception as e:  # feedparser rarely raises, but be safe
        return [], f"feedparser error: {e}"

    if parsed.bozo and not parsed.entries:
        bozo_exc = getattr(parsed, "bozo_exception", None)
        return [], f"feed parse failed: {bozo_exc}"

    entries: list[FeedEntry] = []
    for raw in parsed.entries[:MAX_FEED_ENTRIES_PER_SOURCE]:
        eid = feed_entry_id(raw)
        title = (raw.get("title") or "").strip()
        # arXiv puts the abstract in 'summary'; many feeds do too. Cap length.
        summary = (raw.get("summary") or raw.get("description") or "").strip()
        if len(summary) > 1500:
            summary = summary[:1500] + "..."
        link = (raw.get("link") or "").strip()
        published = (raw.get("published") or raw.get("updated") or "").strip()
        if not eid or not title:
            continue
        entries.append(
            FeedEntry(
                source_id=source.id,
                entry_id=eid,
                title=title,
                summary=summary,
                link=link,
                published=published,
            )
        )
    return entries, ""


def detect_new_entries(
    feed_sources: list[Source],
    state: dict[str, dict],
) -> tuple[list[FeedEntry], list[tuple[Source, str]], dict[str, dict]]:
    """Read every feed, compare each entry id to seen-set in state, return new entries."""
    new_entries: list[FeedEntry] = []
    errors: list[tuple[Source, str]] = []
    updated_state = dict(state)
    now = datetime.now(timezone.utc).isoformat()

    for source in feed_sources:
        entries, err = fetch_feed(source)
        if err:
            errors.append((source, err))
            continue

        prior = state.get(source.id, {})
        seen: set[str] = set(prior.get("seen_ids", []))

        record = dict(prior)
        record["last_checked"] = now
        record["url"] = source.url

        new_for_this_source = [e for e in entries if e.entry_id not in seen]
        new_entries.extend(new_for_this_source)

        # Update seen-set with everything visible this run. Cap the seen-set
        # so it doesn't grow unboundedly: keep the union of new ids and the
        # most recent N of the prior set.
        all_ids = list({*seen, *(e.entry_id for e in entries)})
        # Trim to a reasonable size; arXiv etc. roll over fast and old ids
        # stop appearing in feeds anyway.
        record["seen_ids"] = all_ids[-500:]
        updated_state[source.id] = record

    # Bound the total entries we send to Claude in one run.
    if len(new_entries) > MAX_FEED_ENTRIES_PER_RUN:
        new_entries = new_entries[:MAX_FEED_ENTRIES_PER_RUN]

    return new_entries, errors, updated_state


DIGEST_SYSTEM = """You are the research-triage agent for the Responsible Clinical AI documentation site (https://david-j-cox.github.io/ai-ethics-governance-and-guardrails/).

You will be given a batch of new items from a curated set of feeds: arXiv papers (clinical/medical LLM and AI ethics), behavior-analysis journals, JMIR AI, Nature Digital Medicine, the AI Incident Database, and provider blog posts.

Your job is triage. For each item, decide whether it warrants the maintainer's attention for this site, then write a one-line pitch explaining why or mark it not relevant.

Relevance bar: an item is relevant if a reasonable maintainer of this site would want to read the paper, incident, or post in the next two weeks because it could change a recommendation, surface a new failure mode, or reflect a real-world deployment lesson. Be selective. Most arXiv papers will not pass this bar; that's expected.

Specifically prefer items that:
- Address evaluation methodology, hallucination/grounding, bias and subgroup harm, safety architecture, or audit/logging in clinical or behavioral-health LLM systems
- Document concrete deployment lessons or incidents (especially failure modes)
- Move the state of the art on agentic clinical AI, RAG over patient records, structured clinical output, or clinical decision support
- Come from ABA / behavioral-health / mental-health domains specifically (the domain spotlight on this site)
- Reflect substantive provider capability/safety updates that affect HIPAA-aligned deployment

Specifically de-prioritize:
- General LLM benchmark results not tied to clinical use
- Theoretical work without clinical implication
- Press releases, marketing posts, or roadmap announcements without substance
- Duplicates of items you've already pitched in this batch (mark the second one not relevant with a note about the first)

For each item, return JSON with:
- entry_id: pass through unchanged
- relevant: true or false
- pitch: one sentence, maximum ~30 words. If not relevant, leave empty string.

Be honest about not-relevant items. A good batch may have 3-10 relevant items out of 50. The maintainer's time is the scarce resource."""


DIGEST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "entry_id": {"type": "string"},
                    "relevant": {"type": "boolean"},
                    "pitch": {"type": "string"},
                },
                "required": ["entry_id", "relevant", "pitch"],
            },
        },
    },
    "required": ["items"],
}


def build_digest_user_message(entries: list[FeedEntry]) -> str:
    parts: list[str] = []
    parts.append(f"# Triage batch ({len(entries)} new items)\n")
    parts.append(
        "For each item, decide relevant / not relevant and write a one-line pitch "
        "if relevant. Return JSON matching the schema. The `entry_id` field for each "
        "response item must match the `entry_id` of the corresponding input item exactly.\n"
    )
    for e in entries:
        parts.append(f"## entry_id: {e.entry_id}")
        parts.append(f"**source:** {e.source_id}")
        parts.append(f"**title:** {e.title}")
        if e.published:
            parts.append(f"**published:** {e.published}")
        if e.link:
            parts.append(f"**link:** {e.link}")
        if e.summary:
            parts.append(f"**abstract / summary:**\n{e.summary}")
        parts.append("")
    return "\n".join(parts)


def call_claude_for_digest(
    client: Anthropic, entries: list[FeedEntry]
) -> tuple[list[TriagedEntry], str]:
    if not entries:
        return [], ""

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": DIGEST_SCHEMA},
            },
            system=[
                {
                    "type": "text",
                    "text": DIGEST_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": build_digest_user_message(entries)}],
        ) as stream:
            final = stream.get_final_message()
    except APIError as e:
        return [], f"Claude API error: {e}"

    text_blocks = [b.text for b in final.content if b.type == "text"]
    if not text_blocks:
        return [], "no text output from model"

    raw = text_blocks[0].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return [], f"could not parse JSON output: {e}\nraw: {raw[:500]}"

    by_id = {e.entry_id: e for e in entries}
    triaged: list[TriagedEntry] = []
    for item in data.get("items", []):
        eid = item.get("entry_id", "")
        entry = by_id.get(eid)
        if not entry:
            continue
        triaged.append(
            TriagedEntry(
                entry=entry,
                relevant=bool(item.get("relevant", False)),
                pitch=item.get("pitch", "").strip(),
            )
        )
    return triaged, ""


# =====================================================================
# Git + GitHub helpers
# =====================================================================


def run_git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=check,
    )
    return result.stdout.strip()


def github_repo_slug() -> str | None:
    slug = os.environ.get("GITHUB_REPOSITORY")
    if slug:
        return slug
    try:
        url = run_git("config", "--get", "remote.origin.url")
    except subprocess.CalledProcessError:
        return None
    if url.startswith("git@github.com:"):
        url = url.removeprefix("git@github.com:")
    elif "github.com/" in url:
        url = url.split("github.com/", 1)[1]
    return url.removesuffix(".git").strip()


def resolve_base_branch(repo: str, token: str) -> str:
    """Return the repo's default branch via the GitHub API.

    Falls back to GITHUB_BASE_REF, then to the literal string 'main'.
    The env-var fallback exists for local dev; in CI we always hit the API
    so we get the *current* default branch (not a stale env value).
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"https://api.github.com/repos/{repo}", headers=headers
            )
        if resp.status_code < 300:
            data = resp.json()
            default = data.get("default_branch")
            if default:
                return default
    except httpx.HTTPError as e:
        print(f"[pr] could not query default branch: {e}")

    env_base = (os.environ.get("GITHUB_BASE_REF") or "").strip()
    return env_base or "main"


def open_pr(branch: str, title: str, body: str, labels: list[str]) -> str | None:
    repo = github_repo_slug()
    token = os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        print("[pr] missing GITHUB_REPOSITORY or GITHUB_TOKEN; skipping PR creation")
        return None

    base = resolve_base_branch(repo, token)
    print(f"[pr] opening PR: head={branch} base={base} repo={repo}")

    payload = {"title": title, "head": branch, "base": base, "body": body}
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"https://api.github.com/repos/{repo}/pulls",
            headers=headers,
            json=payload,
        )
    if resp.status_code >= 300:
        print(f"[pr] PR creation failed: {resp.status_code} {resp.text}")
        return None

    pr = resp.json()
    pr_url = pr.get("html_url")
    pr_number = pr.get("number")

    if pr_number and labels:
        with httpx.Client(timeout=30.0) as client:
            client.post(
                f"https://api.github.com/repos/{repo}/issues/{pr_number}/labels",
                headers=headers,
                json={"labels": labels},
            )
    return pr_url


def push_state_only(target_branch: str) -> bool:
    """Stage agent/state.json and push directly to target_branch.

    Used to persist state when there's nothing PR-worthy. Without this, every
    run on an empty seen-set re-discovers the same content, re-pays the LLM
    cost, and never bootstraps. Returns True if anything was pushed.

    The target_branch must already exist remotely. We pull --rebase first
    so we don't conflict with parallel commits.
    """
    run_git("add", "agent/state.json")
    diff = run_git("diff", "--cached", "--name-only")
    if not diff:
        return False

    run_git("config", "user.email", "noreply@github.com")
    run_git("config", "user.name", "source-monitor[bot]")
    run_git("commit", "-m", "chore(agent): persist source-monitor state")

    # Make sure we're on target_branch and up to date with remote before push.
    current = run_git("rev-parse", "--abbrev-ref", "HEAD")
    if current != target_branch:
        # Detached or different branch; create/checkout target.
        try:
            run_git("checkout", target_branch)
        except subprocess.CalledProcessError:
            run_git("checkout", "-b", target_branch, f"origin/{target_branch}")

    # Try to push; if rejected for being behind, rebase and retry once.
    try:
        run_git("push", "origin", target_branch)
    except subprocess.CalledProcessError:
        run_git("fetch", "origin", target_branch)
        run_git("rebase", f"origin/{target_branch}")
        run_git("push", "origin", target_branch)
    return True


def commit_branch_and_open_pr(
    branch_prefix: str,
    files_to_stage: list[str],
    commit_msg: str,
    pr_title: str,
    pr_body: str,
    labels: list[str],
) -> str | None:
    """Stage given files, commit on a fresh branch, push, open PR. Returns PR URL or None.

    Returns None if there's nothing staged (caller should treat as no-op).
    Restores HEAD to the original branch on the way out so a second pipeline
    can run cleanly in the same process.
    """
    original_branch = run_git("rev-parse", "--abbrev-ref", "HEAD")

    for f in files_to_stage:
        run_git("add", f)

    diff = run_git("diff", "--cached", "--name-only")
    if not diff:
        return None

    branch = f"{branch_prefix}-{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M')}"
    run_git("config", "user.email", "noreply@github.com")
    run_git("config", "user.name", "source-monitor[bot]")
    run_git("checkout", "-b", branch)
    run_git("commit", "-m", commit_msg)
    run_git("push", "origin", branch)

    pr_url = open_pr(branch, pr_title, pr_body, labels)

    # Return to base so the next pipeline starts clean.
    run_git("checkout", original_branch)

    return pr_url


# =====================================================================
# PR body builders
# =====================================================================


def build_source_pr_body(
    reports: list[SourceReport],
    errors: list[tuple[Source, str]],
    applied_messages: list[str],
    skipped_messages: list[str],
    llms_txt_touched: set[str],
) -> str:
    lines: list[str] = []
    lines.append("Automated source-monitor PR. Review every change before merging.\n")
    lines.append("This PR was opened by the weekly source-monitoring agent.")
    lines.append("It updates `agent/state.json` with new content hashes for tracked sources,")
    lines.append("and proposes edits to affected docs based on detected source changes.\n")
    lines.append("---\n")

    if reports:
        lines.append("## Source changes detected\n")
        for r in reports:
            lines.append(f"### `{r.source.id}`")
            lines.append(f"<{r.source.url}>\n")
            if r.error:
                lines.append(f"_Error during analysis: {r.error}_\n")
                continue
            lines.append(f"**Summary.** {r.summary}\n")
            if not r.edits:
                lines.append("_No edits proposed._\n")
                continue
            lines.append("**Proposed edits:**\n")
            for e in r.edits:
                lines.append(f"- `{e.path}` ({e.patch_kind}): {e.rationale}")
            lines.append("")

    if applied_messages:
        lines.append("## Edits applied in this PR\n")
        for m in applied_messages:
            lines.append(f"- {m}")
        lines.append("")

    if llms_txt_touched:
        lines.append("## llms.txt review needed\n")
        lines.append("This PR edited files referenced from `docs/llms.txt`. Confirm")
        lines.append("the curated index still accurately describes them, and update")
        lines.append("`docs/llms.txt` in this branch if the framing has shifted.\n")
        for p in sorted(llms_txt_touched):
            lines.append(f"- `{p}`")
        lines.append("")

    if skipped_messages:
        lines.append("## Edits skipped (require human attention)\n")
        for m in skipped_messages:
            lines.append(f"- {m}")
        lines.append("")

    if errors:
        lines.append("## Fetch errors\n")
        lines.append("These sources could not be fetched this run. State was not updated for them;")
        lines.append("they will be retried on the next run.\n")
        for s, msg in errors:
            lines.append(f"- `{s.id}` (<{s.url}>): {msg}")
        lines.append("")

    lines.append("---")
    lines.append(f"Generated by `agent/monitor.py` on {datetime.now(timezone.utc).isoformat()}.")
    return "\n".join(lines)


def build_digest_pr_body(
    triaged: list[TriagedEntry],
    feed_errors: list[tuple[Source, str]],
    triage_error: str,
    total_new_entries: int,
) -> str:
    relevant = [t for t in triaged if t.relevant and t.pitch]
    not_relevant_count = sum(1 for t in triaged if not t.relevant)

    lines: list[str] = []
    lines.append("Weekly research digest. Pointer-only PR; merge to acknowledge.\n")
    lines.append("This PR is opened by the source-monitoring agent's feed pipeline. It does not")
    lines.append("propose edits. The body below lists items from this week's feeds that the")
    lines.append("triage step thinks are worth your attention.\n")
    lines.append("Use it as input. Decide what (if anything) to read, then bring substantive")
    lines.append("findings into the site as a normal docs edit on a separate branch.\n")
    lines.append("---\n")

    lines.append(f"**Items inspected this run:** {total_new_entries}")
    lines.append(f"**Triaged relevant:** {len(relevant)}")
    lines.append(f"**Triaged not relevant:** {not_relevant_count}\n")

    if triage_error:
        lines.append(f"_Triage error: {triage_error}_\n")

    if relevant:
        lines.append("## Relevant items\n")
        # Group by source for readability.
        by_source: dict[str, list[TriagedEntry]] = {}
        for t in relevant:
            by_source.setdefault(t.entry.source_id, []).append(t)
        for source_id in sorted(by_source.keys()):
            lines.append(f"### `{source_id}`\n")
            for t in by_source[source_id]:
                title = t.entry.title.replace("\n", " ").strip()
                if t.entry.link:
                    lines.append(f"- [{title}]({t.entry.link})")
                else:
                    lines.append(f"- {title}")
                if t.pitch:
                    lines.append(f"  - {t.pitch}")
            lines.append("")
    else:
        lines.append("_No items triaged as relevant this week._\n")

    if feed_errors:
        lines.append("## Feed errors\n")
        lines.append("These feeds could not be fetched this run. They will be retried next run.\n")
        for s, msg in feed_errors:
            lines.append(f"- `{s.id}` (<{s.url}>): {msg}")
        lines.append("")

    lines.append("---")
    lines.append(f"Generated by `agent/monitor.py` on {datetime.now(timezone.utc).isoformat()}.")
    return "\n".join(lines)


# =====================================================================
# Main
# =====================================================================


def main(argv: Iterable[str] = ()) -> int:
    sources = load_sources()
    state = load_state()

    watch_sources = [s for s in sources if s.type in ("html", "link-check")]
    feed_sources = [s for s in sources if s.type == "feed"]
    print(
        f"[monitor] loaded {len(sources)} sources "
        f"({len(watch_sources)} watch, {len(feed_sources)} feeds); "
        f"{len(state)} prior state entries"
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    anthropic_client = Anthropic(api_key=api_key) if api_key else None

    # ------------- Pipeline A: source watch -------------

    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=HTTP_TIMEOUT,
        follow_redirects=True,
    ) as http:
        changes, watch_errors, state_after_watch = detect_source_changes(
            watch_sources, state, http
        )

    print(
        f"[monitor] watch: {len(changes)} changed, {len(watch_errors)} fetch errors"
    )

    reports: list[SourceReport] = []
    if changes:
        if not anthropic_client:
            print("[monitor] ANTHROPIC_API_KEY not set; cannot analyze source changes")
            return 1
        for change in changes:
            print(f"[monitor] watch: analyzing {change.source.id}")
            reports.append(call_claude_for_source(anthropic_client, change))

    applied_messages: list[str] = []
    applied_paths: set[str] = set()
    skipped_messages: list[str] = []
    for r in reports:
        for e in r.edits:
            ok, msg = apply_edit(e)
            if ok:
                applied_messages.append(msg)
                applied_paths.add(e.path)
            else:
                skipped_messages.append(msg)

    # Persist watch-pipeline state changes before pipeline B reads state again.
    save_state(state_after_watch)

    watch_pr_url: str | None = None
    if changes or watch_errors or applied_messages:
        files = ["agent/state.json"]
        if applied_messages:
            files.append("docs/")
        commit_msg = (
            f"chore(agent): weekly source check ({len(changes)} changed, "
            f"{len(applied_messages)} edits applied)"
        )
        watch_pr_url = commit_branch_and_open_pr(
            branch_prefix="agent/source-update",
            files_to_stage=files,
            commit_msg=commit_msg,
            pr_title=f"Weekly source check: {len(changes)} change(s) detected",
            pr_body=build_source_pr_body(
                reports,
                watch_errors,
                applied_messages,
                skipped_messages,
                applied_paths & llms_txt_referenced_pages(),
            ),
            labels=["agent", "source-monitor"],
        )
        if watch_pr_url:
            print(f"[monitor] watch PR: {watch_pr_url}")

    # ------------- Pipeline B: feed digest -------------

    # Re-read state from disk (pipeline A may have committed changes; we want
    # the on-disk version so the next run sees consistent state regardless).
    state_for_feeds = load_state()
    new_entries, feed_errors, state_after_feeds = detect_new_entries(
        feed_sources, state_for_feeds
    )
    print(
        f"[monitor] feeds: {len(new_entries)} new entries, "
        f"{len(feed_errors)} feed errors"
    )

    triaged: list[TriagedEntry] = []
    triage_error = ""
    if new_entries:
        if not anthropic_client:
            print("[monitor] ANTHROPIC_API_KEY not set; cannot triage feed entries")
            return 1
        triaged, triage_error = call_claude_for_digest(anthropic_client, new_entries)

    save_state(state_after_feeds)

    digest_pr_url: str | None = None
    relevant_count = sum(1 for t in triaged if t.relevant and t.pitch)
    # Open a digest PR if anything happened: new entries seen, triage findings,
    # or feed errors worth surfacing. Skip when the run is genuinely empty.
    if new_entries or feed_errors:
        commit_msg = (
            f"chore(agent): weekly research digest "
            f"({len(new_entries)} new, {relevant_count} relevant)"
        )
        digest_pr_url = commit_branch_and_open_pr(
            branch_prefix="agent/research-digest",
            files_to_stage=["agent/state.json"],
            commit_msg=commit_msg,
            pr_title=(
                f"Weekly research digest: {relevant_count} relevant of "
                f"{len(new_entries)} new"
            ),
            pr_body=build_digest_pr_body(
                triaged, feed_errors, triage_error, len(new_entries)
            ),
            labels=["agent", "research-digest"],
        )
        if digest_pr_url:
            print(f"[monitor] digest PR: {digest_pr_url}")

    # If no PR was opened (clean week, OR PR creation failed), still push the
    # state file so we don't re-discover the same content next run. Without
    # this, a PR-creation bug or a clean first run leaves seen_ids empty
    # forever and we re-pay the LLM cost every week.
    if not watch_pr_url and not digest_pr_url:
        token = os.environ.get("GITHUB_TOKEN")
        repo = github_repo_slug()
        target = resolve_base_branch(repo, token) if (repo and token) else "main"
        if push_state_only(target):
            print(f"[monitor] no PRs opened; pushed state directly to {target}")
        else:
            print("[monitor] no PRs opened this run; nothing to commit")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
