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
import time
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
    if not STATE_PATH.exists():
        return {}
    # Self-heal a state.json mangled by a server-side 3-way merge (where
    # custom git merge drivers can't run). No-op if the file is already valid.
    from repair_state import repair

    if repair(STATE_PATH):
        print("[monitor] repaired corrupted state.json before load")
    return json.loads(STATE_PATH.read_text())


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
    """Fetch and parse a feed. Returns (entries, error).

    We fetch the bytes ourselves via httpx rather than letting feedparser fetch
    the URL directly, for two reasons proven against the live feeds:

    - Cross-host redirects. Springer's ``search.rss`` answers with a 303 that
      feedparser does not follow, so the feed parsed as empty/invalid. httpx
      with ``follow_redirects`` resolves it to valid XML.
    - Rate limiting. arXiv returns a plain-text "Rate exceeded" body on HTTP 429,
      which otherwise surfaces as a misleading XML parse error ("mismatched tag").
      Seeing the status lets us back off and retry instead of reporting a parse
      failure.
    """
    headers = {"User-Agent": USER_AGENT}
    content: bytes | None = None
    last_error = ""
    for attempt in range(3):
        try:
            with httpx.Client(
                headers=headers, timeout=HTTP_TIMEOUT, follow_redirects=True
            ) as client:
                resp = client.get(source.url)
        except httpx.HTTPError as e:
            last_error = f"fetch error: {e}"
            time.sleep(3 * (attempt + 1))
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            # arXiv asks clients to slow down; back off and retry.
            last_error = f"http {resp.status_code} (rate limited or server error)"
            time.sleep(5 * (attempt + 1))
            continue
        if resp.status_code >= 400:
            return [], f"http {resp.status_code}"
        content = resp.content
        break
    if content is None:
        return [], last_error or "feed fetch failed after retries"

    try:
        parsed = feedparser.parse(content)
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

    for i, source in enumerate(feed_sources):
        # Be polite between requests; arXiv in particular rate-limits bursts.
        if i > 0:
            time.sleep(3)
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
# Pipeline C: research-derived edits
# =====================================================================
#
# Goal: take the top-N relevant items from pipeline B's triage, fetch each
# one's full content, and ask Claude to draft an edit (or decline) on
# specific docs/ pages. Result is a third PR the maintainer reviews.
#
# Constraints baked in below:
#   - Authoritative summary pages (regulatory.md, frameworks.md) are
#     off-limits; research findings get appended elsewhere or noted, not
#     used to rewrite regulatory/standards prose.
#   - Hedging language is mandatory and source-type-specific. arXiv items
#     must be cited as preprints; AIID items as incident reports; journal
#     articles as peer-reviewed.
#   - Cap at MAX_RESEARCH_EDITS items per run regardless of triage volume.

MAX_RESEARCH_EDITS = 10

# Pages that must not be edited from research-derived content. They
# summarize external authorities and changing them based on a paper or
# incident would be a quality regression.
RESEARCH_EDIT_DENYLIST: tuple[str, ...] = (
    "docs/reference/regulatory.md",
    "docs/reference/frameworks.md",
    "docs/foundations/principles.md",  # load-bearing commitments; conservative
)

# Source-authority ranking used to pick the top-N when more than
# MAX_RESEARCH_EDITS items pass triage. Higher = more authoritative.
SOURCE_AUTHORITY: dict[str, int] = {
    "ai-incident-database": 5,
    "jmir-ai": 5,
    "nature-digital-medicine": 5,
    "behavior-analysis-in-practice": 4,
    "journal-applied-behavior-analysis": 4,
    "arxiv": 2,
}


@dataclass
class ResearchEdit:
    """A drafted edit derived from a research-feed item."""
    entry: FeedEntry
    fetched_content: str
    summary: str
    edits: list[ProposedEdit] = field(default_factory=list)
    error: str = ""


def rank_for_research_edits(triaged: list[TriagedEntry]) -> list[TriagedEntry]:
    """Return relevant items ranked by source authority, capped at MAX_RESEARCH_EDITS."""
    relevant = [t for t in triaged if t.relevant and t.pitch]
    relevant.sort(
        key=lambda t: SOURCE_AUTHORITY.get(t.entry.source_id, 1),
        reverse=True,
    )
    return relevant[:MAX_RESEARCH_EDITS]


def fetch_research_content(entry: FeedEntry, client: httpx.Client) -> tuple[str, str]:
    """Fetch the link target and extract main content. Returns (content, error).

    Trafilatura handles abstract pages (arXiv, AIID, journals) well. Full PDFs
    are skipped — we accept that abstract + feed summary is enough context.
    """
    if not entry.link:
        return "", "no link on entry"
    try:
        resp = client.get(entry.link, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        return "", f"fetch error: {e}"

    extracted = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
    if not extracted:
        # Fallback: use the feed-supplied summary so we don't drop the item
        # entirely just because the link target is JS-heavy.
        if entry.summary:
            return entry.summary, ""
        return "", "trafilatura returned no content and no feed summary available"
    return extracted.strip()[:12000], ""


def build_site_map() -> str:
    """Return a compact markdown index of docs/ pages for Claude.

    Per page: title (first H1), section headings (H2/H3), llms.txt-curated flag.
    Skips index.md files since they're navigation, not content. Output capped
    at ~5KB to keep prompt tokens bounded.
    """
    import re

    curated = llms_txt_referenced_pages()
    lines: list[str] = ["# Site map (docs/)", ""]

    for path in sorted(DOCS_ROOT.rglob("*.md")):
        rel = f"docs/{path.relative_to(DOCS_ROOT)}"
        if path.name == "index.md":
            continue
        if rel in RESEARCH_EDIT_DENYLIST:
            # Still list them but mark as no-edit so Claude doesn't pick them.
            denied = " (DO NOT EDIT — authoritative summary)"
        else:
            denied = ""
        is_curated = " [curated]" if rel in curated else ""

        text = path.read_text()
        title = ""
        h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()
        sections = re.findall(r"^#{2,3}\s+(.+)$", text, re.MULTILINE)

        lines.append(f"## `{rel}`{is_curated}{denied}")
        if title:
            lines.append(f"_{title}_")
        if sections:
            preview = sections[:8]
            lines.append("Sections: " + " · ".join(s.strip() for s in preview))
        lines.append("")

    blob = "\n".join(lines)
    if len(blob) > 6000:
        blob = blob[:6000] + "\n\n_(site map truncated)_\n"
    return blob


RESEARCH_EDIT_SYSTEM = """You are the research-integration agent for the Responsible Clinical AI documentation site.

Each invocation gives you ONE relevant item from a curated feed (arXiv, AIID, JMIR, Nature Digital Medicine, behavior-analysis journals, provider blogs) and asks: should this update the site, and if so, where and how?

You have:
- The item's title, source, link, and extracted content (often an abstract).
- A site map of docs/ pages with their titles and section headings.
- The current contents of any pages you decide are candidate edit targets.

Your output is one of:
- One or more `replace` / `append` edits on docs/ pages.
- A `no-edit` decision with rationale (e.g., "interesting but not actionable yet", "already covered on docs/X.md").

Hard rules:
1. **Conservative bar.** Edit only when the item materially changes a recommendation on the site, surfaces a new failure mode worth listing, or adds a concrete deployment lesson. Most relevant items will be `no-edit` with a "would-be useful but not strong enough" rationale. That is correct.

2. **Hedge by source type.** Cite items appropriately:
   - arXiv → "a 2026 preprint reports..." (NOT peer-reviewed)
   - JMIR AI / Nature Digital Medicine / behavior-analysis journals → "X et al. (YEAR) report..." (peer-reviewed)
   - AI Incident Database → "the AI Incident Database documents..." (incident report, not finding)
   - Provider blog → "VENDOR's NAME (YEAR) describes..." (vendor source)

3. **Authoritative pages are off-limits.** You will see pages marked `DO NOT EDIT — authoritative summary`. Never propose edits to these. Pick a different page or `no-edit`.

4. **Small diffs.** Prefer surgical find/replace or appending one bullet under an existing list. No new sections, no reordering, no rewriting paragraphs.

5. **Match the page's voice.** The site is plain English, opinionated, no em dashes, written for both builders and buyers.

6. **Cite the source.** Every edit must include a link to the item in its replace text or append text. Format: `[short descriptor](URL)`.

7. **Never invent.** If the item's claims are unclear from the extracted content, `no-edit` and explain.

8. **One link's worth, not a synthesis.** Don't try to write multi-source paragraphs. Each edit references this one item.

Return strict JSON matching the schema you'll be shown."""


RESEARCH_EDIT_SCHEMA = {
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


def build_research_user_message(
    entry: FeedEntry, content: str, site_map: str
) -> str:
    parts: list[str] = []
    parts.append("# Research item")
    parts.append("")
    parts.append(f"**Source:** {entry.source_id}")
    parts.append(f"**Title:** {entry.title}")
    parts.append(f"**Link:** {entry.link}")
    if entry.published:
        parts.append(f"**Published:** {entry.published}")
    parts.append("")
    parts.append("## Extracted content")
    parts.append("")
    parts.append("```")
    parts.append(content[:8000])
    parts.append("```")
    parts.append("")
    parts.append(site_map)
    parts.append("")
    parts.append(
        "Decide: which docs/ page(s), if any, should integrate this item? Return "
        "edits or no-edit with rationale. Then, in a follow-up turn, you'll see "
        "the full contents of any page paths you reference."
    )
    return "\n".join(parts)


def call_claude_for_research_edit(
    client: Anthropic, entry: FeedEntry, content: str, site_map: str
) -> ResearchEdit:
    """Two-pass approach would be ideal; we collapse to one pass by sending the
    site map up front and letting Claude pick paths it sees there. We then
    read the chosen pages, apply edits, and validate."""
    user_text = build_research_user_message(entry, content, site_map)

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": RESEARCH_EDIT_SCHEMA},
            },
            system=[
                {
                    "type": "text",
                    "text": RESEARCH_EDIT_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_text}],
        ) as stream:
            final = stream.get_final_message()
    except APIError as e:
        return ResearchEdit(
            entry=entry, fetched_content=content, summary="", error=f"Claude API error: {e}"
        )

    text_blocks = [b.text for b in final.content if b.type == "text"]
    if not text_blocks:
        return ResearchEdit(
            entry=entry, fetched_content=content, summary="", error="no text output from model"
        )
    raw = text_blocks[0].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return ResearchEdit(
            entry=entry,
            fetched_content=content,
            summary="",
            error=f"could not parse JSON output: {e}\nraw: {raw[:500]}",
        )

    edits = []
    for e in data.get("edits", []):
        path = e.get("path", "")
        # Hard-enforce the denylist regardless of what Claude returned.
        if path in RESEARCH_EDIT_DENYLIST and e.get("patch_kind") != "no-edit":
            edits.append(
                ProposedEdit(
                    path=path,
                    rationale=(
                        f"Edit suppressed: `{path}` is on the research-edit denylist "
                        f"(authoritative summary page). Original rationale: {e.get('rationale','')}"
                    ),
                    patch_kind="no-edit",
                )
            )
            continue
        edits.append(
            ProposedEdit(
                path=path,
                rationale=e.get("rationale", ""),
                patch_kind=e.get("patch_kind", "no-edit"),
                find=e.get("find", ""),
                replace=e.get("replace", ""),
            )
        )

    return ResearchEdit(
        entry=entry,
        fetched_content=content,
        summary=data.get("summary", ""),
        edits=edits,
    )


def run_research_edits_pipeline(
    triaged: list[TriagedEntry],
    anthropic_client: Anthropic | None,
    http: httpx.Client,
) -> list[ResearchEdit]:
    """Returns the list of ResearchEdit results (including no-edit decisions)."""
    if not anthropic_client:
        return []

    candidates = rank_for_research_edits(triaged)
    if not candidates:
        return []

    print(f"[monitor] research-edits: {len(candidates)} candidates after ranking")
    site_map = build_site_map()
    results: list[ResearchEdit] = []
    for t in candidates:
        print(f"[monitor] research-edits: fetching {t.entry.entry_id[:60]}")
        content, fetch_err = fetch_research_content(t.entry, http)
        if fetch_err:
            results.append(
                ResearchEdit(
                    entry=t.entry,
                    fetched_content="",
                    summary="",
                    error=f"fetch failed: {fetch_err}",
                )
            )
            continue
        result = call_claude_for_research_edit(anthropic_client, t.entry, content, site_map)
        results.append(result)
    return results


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


def build_edit_pr_body(
    edit: ProposedEdit, source_label: str, decision_summary: str
) -> str:
    """PR body for a single proposed doc edit. Self-contained so the change can
    be reviewed without opening files: includes rationale, driving source, and
    the exact find/replace (or appended) text."""
    lines: list[str] = []
    lines.append("Automated proposed edit from the weekly source monitor.")
    lines.append(
        "**Merge to accept, close to decline, or push to this branch to modify.**\n"
    )
    lines.append(f"- Target file: `{edit.path}`")
    lines.append(f"- Change type: `{edit.patch_kind}`")
    lines.append(f"- Driven by: {source_label}")
    if edit.path in llms_txt_referenced_pages():
        lines.append(
            "- Note: this page is referenced by `llms.txt`; double-check that "
            "summary stays accurate."
        )
    lines.append("")
    lines.append(f"**Rationale.** {edit.rationale}\n")
    if decision_summary:
        lines.append(f"**Decision context.** {decision_summary}\n")
    if edit.patch_kind == "replace":
        lines.append("**Find:**")
        lines.append("```")
        lines.append(edit.find)
        lines.append("```")
        lines.append("**Replace with:**")
        lines.append("```")
        lines.append(edit.replace)
        lines.append("```")
    elif edit.patch_kind == "append":
        lines.append("**Appended to end of file:**")
        lines.append("```")
        lines.append(edit.replace)
        lines.append("```")
    return "\n".join(lines)


def open_edit_pr(
    edit: ProposedEdit,
    *,
    index: int,
    source_label: str,
    decision_summary: str,
) -> tuple[str | None, str, bool]:
    """Apply ONE proposed edit on its own branch and open a dedicated PR.

    Each proposed doc change becomes an independent PR so a human can accept it
    (merge), decline it (close), or modify it (push to the branch) without
    coupling it to any other edit or to the state.json bookkeeping. That
    decoupling matters: declining an edit must never strand the bookkeeping,
    or the monitor re-flags the same source next week.

    Returns (pr_url_or_None, message, applied_ok). 'no-edit' proposals and
    apply failures return applied_ok=False with a descriptive message and never
    touch git. Branches off the currently checked-out branch and returns to it.
    """
    import re

    if edit.patch_kind == "no-edit":
        return None, f"skip {edit.path}: {edit.rationale}", False

    original_branch = run_git("rev-parse", "--abbrev-ref", "HEAD")
    ok, msg = apply_edit(edit)
    if not ok:
        # apply_edit writes the file only on success, so the tree is unchanged.
        return None, msg, False

    slug = re.sub(r"[^a-z0-9]+", "-", edit.path.lower()).strip("-")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    branch = f"agent/edit-{slug}-{stamp}-{index}"

    run_git("config", "user.email", "noreply@github.com")
    run_git("config", "user.name", "source-monitor[bot]")
    run_git("checkout", "-b", branch)
    run_git("add", edit.path)
    run_git("commit", "-m", f"docs({edit.path}): {edit.patch_kind} per source monitor")
    run_git("push", "origin", branch)

    pr_url = open_pr(
        branch,
        f"Proposed edit: {edit.path}",
        build_edit_pr_body(edit, source_label, decision_summary),
        ["agent", "proposed-edit"],
    )

    # Return to base so the working tree is clean for the next edit.
    run_git("checkout", original_branch)
    return pr_url, msg, True


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


def build_run_summary(
    *,
    watch_sources: list[Source],
    feed_sources: list[Source],
    changes: list[SourceChange],
    reports: list[SourceReport],
    watch_errors: list[tuple[Source, str]],
    applied_messages: list[str],
    skipped_messages: list[str],
    watch_pr_url: str | None,
    new_entries: list[FeedEntry],
    triaged: list[TriagedEntry],
    feed_errors: list[tuple[Source, str]],
    triage_error: str,
    digest_pr_url: str | None,
    research_results: list[ResearchEdit] | None = None,
    research_applied: list[str] | None = None,
    research_skipped: list[str] | None = None,
    edit_prs: list[tuple[str, str, str]] | None = None,
) -> str:
    """One markdown blob describing what this run did. Used by job summary,
    status issue body, and email body. Always produced, including clean weeks.

    edit_prs is a list of (path, rationale, pr_url) for each proposed doc edit
    opened as its own PR this run."""
    research_results = research_results or []
    research_applied = research_applied or []
    research_skipped = research_skipped or []
    edit_prs = edit_prs or []
    relevant = [t for t in triaged if t.relevant and t.pitch]
    pr_count = (
        sum(1 for u in (watch_pr_url, digest_pr_url) if u) + len(edit_prs)
    )
    err_count = len(watch_errors) + len(feed_errors)

    if changes or len(relevant) or err_count:
        headline = (
            f"{len(changes)} source change(s), {len(relevant)} relevant feed item(s), "
            f"{err_count} error(s)"
        )
    else:
        headline = "Clean week — nothing to review"

    lines: list[str] = []
    lines.append(f"# Weekly source monitor — {datetime.now(timezone.utc).date().isoformat()}")
    lines.append("")
    lines.append(f"**{headline}.**")
    lines.append("")

    # ---- Executive summary: skim this first; full detail follows below. ----
    lines.append("## Executive summary")
    lines.append("")

    # 1) Proposed edits you can accept/decline this run.
    if edit_prs:
        lines.append(
            f"**{len(edit_prs)} proposed edit(s)** — merge the PR to accept, "
            "close it to decline:"
        )
        for path, rationale, url in edit_prs:
            short = rationale if len(rationale) <= 140 else rationale[:137] + "..."
            lines.append(f"- `{path}` — {short} → {url}")
    else:
        lines.append("**Proposed edits:** none this run.")
    lines.append("")

    # 2) Things that need a human (errors + edits that failed to apply).
    attention: list[str] = []
    for s, msg in watch_errors:
        attention.append(f"fetch error — watch `{s.id}`: {msg}")
    for s, msg in feed_errors:
        attention.append(f"feed error — `{s.id}`: {msg}")
    attention.extend(skipped_messages)
    attention.extend(research_skipped)
    if attention:
        lines.append("**Needs your attention:**")
        for a in attention:
            lines.append(f"- {a}")
        lines.append("")

    # 3) What changed at a glance.
    if changes:
        ids = ", ".join(f"`{c.source.id}`" for c in changes)
        lines.append(f"**Source content changed ({len(changes)}):** {ids}.")
    else:
        lines.append("**Source content changed:** none.")
    if relevant:
        top = relevant[:5]
        lines.append(
            f"**Relevant research items ({len(relevant)} of {len(new_entries)} new)** "
            "— top picks:"
        )
        for t in top:
            title = t.entry.title.replace("\n", " ").strip()
            if t.entry.link:
                lines.append(f"- [{title}]({t.entry.link})")
            else:
                lines.append(f"- {title}")
        if len(relevant) > len(top):
            lines.append(
                f"- …and {len(relevant) - len(top)} more (see Research digest below)."
            )
    else:
        lines.append("**Relevant research items:** none.")
    lines.append("")

    lines.append(
        f"- Watch sources checked: **{len(watch_sources)}** "
        f"({len(changes)} changed, {len(watch_errors)} errors)"
    )
    lines.append(
        f"- Feed sources checked: **{len(feed_sources)}** "
        f"({len(new_entries)} new entries, {len(relevant)} relevant, {len(feed_errors)} errors)"
    )
    lines.append(f"- PRs opened this run: **{pr_count}**")
    if watch_pr_url:
        lines.append(f"  - Source-update (state bookkeeping) PR: {watch_pr_url}")
    if digest_pr_url:
        lines.append(f"  - Research-digest (state bookkeeping) PR: {digest_pr_url}")
    for path, _rationale, url in edit_prs:
        lines.append(f"  - Proposed edit `{path}`: {url}")
    if research_results:
        no_edit_count = sum(
            1 for r in research_results for e in r.edits if e.patch_kind == "no-edit"
        )
        edit_count = sum(
            1 for r in research_results for e in r.edits if e.patch_kind != "no-edit"
        )
        lines.append(
            f"- Research-derived edits: **{len(research_results)}** items reviewed, "
            f"{edit_count} drafted, {no_edit_count} declined, "
            f"{len(research_applied)} applied, {len(research_skipped)} skipped"
        )
    lines.append("")

    if reports:
        lines.append("## Source changes and decisions")
        lines.append("")
        for r in reports:
            lines.append(f"### `{r.source.id}` — {r.source.url}")
            if r.error:
                lines.append(f"_Analysis error: {r.error}_")
                lines.append("")
                continue
            lines.append(f"**Summary.** {r.summary}")
            if not r.edits:
                lines.append("_Claude proposed no edits for this change._")
            else:
                no_edits = [e for e in r.edits if e.patch_kind == "no-edit"]
                real_edits = [e for e in r.edits if e.patch_kind != "no-edit"]
                if real_edits:
                    lines.append("**Edits proposed:**")
                    for e in real_edits:
                        lines.append(f"- `{e.path}` ({e.patch_kind}) — {e.rationale}")
                if no_edits:
                    lines.append("**No-edit decisions (why nothing changed for these pages):**")
                    for e in no_edits:
                        lines.append(f"- `{e.path}` — {e.rationale}")
            lines.append("")

    if applied_messages:
        lines.append("## Edits applied this run")
        lines.append("")
        for m in applied_messages:
            lines.append(f"- {m}")
        lines.append("")

    if skipped_messages:
        lines.append("## Edits skipped (need human attention)")
        lines.append("")
        for m in skipped_messages:
            lines.append(f"- {m}")
        lines.append("")

    if relevant:
        lines.append("## Research digest — relevant items")
        lines.append("")
        by_source: dict[str, list[TriagedEntry]] = {}
        for t in relevant:
            by_source.setdefault(t.entry.source_id, []).append(t)
        for source_id in sorted(by_source.keys()):
            lines.append(f"### `{source_id}`")
            for t in by_source[source_id]:
                title = t.entry.title.replace("\n", " ").strip()
                if t.entry.link:
                    lines.append(f"- [{title}]({t.entry.link}) — {t.pitch}")
                else:
                    lines.append(f"- {title} — {t.pitch}")
            lines.append("")

    if research_results:
        lines.append("## Research-derived edits")
        lines.append("")
        for r in research_results:
            link = f"[{r.entry.title.strip()}]({r.entry.link})" if r.entry.link else r.entry.title.strip()
            lines.append(f"### `{r.entry.source_id}` — {link}")
            if r.error:
                lines.append(f"_Error: {r.error}_")
                lines.append("")
                continue
            if r.summary:
                lines.append(f"**Decision summary.** {r.summary}")
            real_edits = [e for e in r.edits if e.patch_kind != "no-edit"]
            no_edits = [e for e in r.edits if e.patch_kind == "no-edit"]
            if real_edits:
                lines.append("**Edits drafted:**")
                for e in real_edits:
                    lines.append(f"- `{e.path}` ({e.patch_kind}) — {e.rationale}")
            if no_edits:
                lines.append("**Declined (why no edit):**")
                for e in no_edits:
                    lines.append(f"- `{e.path}` — {e.rationale}")
            if not r.edits:
                lines.append("_Claude proposed nothing for this item._")
            lines.append("")

    if triage_error:
        lines.append(f"_Triage error: {triage_error}_")
        lines.append("")

    if watch_errors or feed_errors:
        lines.append("## Fetch / feed errors")
        lines.append("")
        for s, msg in watch_errors:
            lines.append(f"- watch `{s.id}` (<{s.url}>): {msg}")
        for s, msg in feed_errors:
            lines.append(f"- feed `{s.id}` (<{s.url}>): {msg}")
        lines.append("")

    lines.append("---")
    lines.append(f"_Generated by `agent/monitor.py` on {datetime.now(timezone.utc).isoformat()}._")
    return "\n".join(lines)


def write_summary_outputs(summary_md: str, *, had_changes: bool, pr_urls: list[str]) -> None:
    """Write the run summary to a path the workflow can pick up, and emit
    GH Actions outputs. No-ops cleanly outside CI."""
    summary_path = os.environ.get("MONITOR_SUMMARY_PATH")
    if summary_path:
        Path(summary_path).write_text(summary_md)
        print(f"[monitor] wrote summary to {summary_path}")

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a") as fh:
            fh.write(f"had_changes={'true' if had_changes else 'false'}\n")
            fh.write(f"pr_count={len(pr_urls)}\n")
            for i, url in enumerate(pr_urls):
                fh.write(f"pr_url_{i}={url}\n")

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a") as fh:
            fh.write(summary_md + "\n")


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
    skipped_messages: list[str] = []
    # (path, rationale, pr_url) for each proposed edit opened as its own PR.
    edit_prs: list[tuple[str, str, str]] = []
    edit_index = 0

    # Persist watch-pipeline state changes before pipeline B reads state again.
    save_state(state_after_watch)

    # Bookkeeping PR: state.json only. This always-mergeable PR records what the
    # monitor saw so it doesn't re-flag the same sources next week. Proposed doc
    # edits are intentionally NOT bundled here — they get their own PRs below so
    # declining one never strands this bookkeeping.
    watch_pr_url: str | None = None
    if changes or watch_errors:
        commit_msg = (
            f"chore(agent): weekly source check "
            f"({len(changes)} changed, state bookkeeping)"
        )
        watch_pr_url = commit_branch_and_open_pr(
            branch_prefix="agent/source-update",
            files_to_stage=["agent/state.json"],
            commit_msg=commit_msg,
            pr_title=f"Weekly source check: {len(changes)} change(s) detected",
            pr_body=build_source_pr_body(reports, watch_errors, [], [], set()),
            labels=["agent", "source-monitor"],
        )
        if watch_pr_url:
            print(f"[monitor] watch bookkeeping PR: {watch_pr_url}")

    # One PR per proposed doc edit so each can be accepted/declined on its own.
    for r in reports:
        for e in r.edits:
            url, msg, ok = open_edit_pr(
                e,
                index=edit_index,
                source_label=f"watch source `{r.source.id}`",
                decision_summary=r.summary,
            )
            edit_index += 1
            if ok:
                applied_messages.append(msg)
                if url:
                    edit_prs.append((e.path, e.rationale, url))
                    print(f"[monitor] edit PR ({e.path}): {url}")
            elif e.patch_kind != "no-edit":
                skipped_messages.append(msg)

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

    # ------------- Pipeline C: research-derived edits -------------

    research_results: list[ResearchEdit] = []
    research_applied: list[str] = []
    research_skipped: list[str] = []
    if triaged:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
        ) as http:
            research_results = run_research_edits_pipeline(triaged, anthropic_client, http)

        # One PR per research-derived edit, same as the watch pipeline, so each
        # can be accepted/declined independently.
        for r in research_results:
            for e in r.edits:
                url, msg, ok = open_edit_pr(
                    e,
                    index=edit_index,
                    source_label=f'research item "{r.entry.title.strip()}"',
                    decision_summary=r.summary,
                )
                edit_index += 1
                if ok:
                    research_applied.append(msg)
                    if url:
                        edit_prs.append((e.path, e.rationale, url))
                        print(f"[monitor] edit PR ({e.path}): {url}")
                elif e.patch_kind != "no-edit":
                    research_skipped.append(msg)
        print(
            f"[monitor] research-edits: {len(research_results)} items reviewed, "
            f"{len(research_applied)} applied, {len(research_skipped)} skipped"
        )

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

    summary_md = build_run_summary(
        watch_sources=watch_sources,
        feed_sources=feed_sources,
        changes=changes,
        reports=reports,
        watch_errors=watch_errors,
        applied_messages=applied_messages,
        skipped_messages=skipped_messages,
        watch_pr_url=watch_pr_url,
        new_entries=new_entries,
        triaged=triaged,
        feed_errors=feed_errors,
        triage_error=triage_error,
        digest_pr_url=digest_pr_url,
        research_results=research_results,
        research_applied=research_applied,
        research_skipped=research_skipped,
        edit_prs=edit_prs,
    )
    pr_urls = [u for u in (watch_pr_url, digest_pr_url) if u] + [u for _, _, u in edit_prs]
    had_changes = bool(
        changes
        or [t for t in triaged if t.relevant]
        or watch_errors
        or feed_errors
        or research_results
    )
    write_summary_outputs(summary_md, had_changes=had_changes, pr_urls=pr_urls)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
