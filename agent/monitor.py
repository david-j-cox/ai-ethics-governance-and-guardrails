"""Source-monitoring agent.

Weekly job that:
  1. Loads source definitions from agent/sources/*.yaml
  2. Fetches each source and compares to last-known content hash in state.json
  3. For changed `html` sources, asks Claude to summarize the change and propose
     edits to the affected docs/ markdown pages
  4. For `link-check` sources, only verifies the URL still resolves
  5. Writes proposed edits to a fresh branch, opens one PR aggregating all
     changed sources, and updates state.json. Never auto-merges.

Design contract:
  - PR-only, never auto-merges. The maintainer is the human in the loop.
  - One run = one PR (or zero, if nothing changed). Aggregates per-source
    sections inside one PR body so a clean week is silent.
  - Each proposed edit cites the source URL, the diff summary, and the
    rationale Claude gave. The maintainer can accept, reject, or edit.
  - Fetch failures are logged and skipped, not fatal. A flaky source on
    week N still lets the agent run on week N+1 from the same baseline.
  - LLM cost is bounded: unchanged sources never trigger an LLM call.
    Changed sources cache the system prompt + per-source affected docs,
    so re-runs on the same diff are near-free.

Environment:
  - ANTHROPIC_API_KEY: required for Claude calls. Supplied via GH Actions
    repo secret.
  - GITHUB_TOKEN: required for opening PRs. Supplied automatically by
    Actions runner.
  - GITHUB_REPOSITORY: "owner/repo" form. Supplied automatically by
    Actions runner. Falls back to git remote parsing for local dev.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import httpx
import trafilatura
import yaml
from anthropic import Anthropic, APIError

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = Path(__file__).resolve().parent
SOURCES_DIR = AGENT_DIR / "sources"
STATE_PATH = AGENT_DIR / "state.json"
DOCS_ROOT = REPO_ROOT / "docs"

USER_AGENT = (
    "responsible-clinical-ai-monitor/1.0 "
    "(+https://github.com/david-j-cox/ai-ethics-governance-and-guardrails)"
)
HTTP_TIMEOUT = 30.0
MODEL = "claude-opus-4-7"
MAX_OUTPUT_TOKENS = 16000
SNAPSHOT_BYTES = 8000  # cap stored extracted text to keep state.json reasonable


@dataclass
class Source:
    id: str
    url: str
    type: str
    cadence: str
    applies_to: list[str]
    notes: str = ""


@dataclass
class FetchResult:
    ok: bool
    content: str = ""
    content_hash: str = ""
    error: str = ""


@dataclass
class SourceChange:
    """A source whose content changed since last run, awaiting LLM analysis."""
    source: Source
    new_content: str
    new_hash: str
    old_snapshot: str  # may be empty on first sight


@dataclass
class ProposedEdit:
    path: str  # repo-relative, e.g. "docs/reference/regulatory.md"
    rationale: str
    patch_kind: str  # "replace" | "append" | "no-edit"
    find: str = ""
    replace: str = ""


@dataclass
class SourceReport:
    """One section of the eventual PR body, plus the edits to apply."""
    source: Source
    summary: str  # 2-3 sentence summary of what changed
    edits: list[ProposedEdit] = field(default_factory=list)
    error: str = ""


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


def fetch(source: Source, client: httpx.Client) -> FetchResult:
    """Fetch source. For html, extract main content via trafilatura."""
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


def detect_changes(
    sources: list[Source],
    state: dict[str, dict],
    client: httpx.Client,
) -> tuple[list[SourceChange], list[tuple[Source, str]], dict[str, dict]]:
    """Fetch each source, return (changes, errors, updated_state).

    `updated_state` reflects every source we successfully fetched, even unchanged
    ones (we update last_checked timestamps).
    """
    changes: list[SourceChange] = []
    errors: list[tuple[Source, str]] = []
    updated_state = dict(state)
    now = datetime.now(timezone.utc).isoformat()

    for source in sources:
        result = fetch(source, client)
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


SYSTEM_PROMPT = """You are the source-monitoring agent for the Responsible Clinical AI documentation site (https://david-j-cox.github.io/ai-ethics-governance-and-guardrails/).

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


REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {
            "type": "string",
            "description": "2-3 sentence summary of what changed in the source and whether the site needs updates.",
        },
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


def build_user_message(change: SourceChange) -> str:
    parts: list[str] = []
    parts.append(f"# Source change\n")
    parts.append(f"**ID:** {change.source.id}")
    parts.append(f"**URL:** {change.source.url}")
    parts.append(f"**Notes:** {change.source.notes.strip() or '(none)'}\n")

    if change.old_snapshot:
        parts.append("## Prior snapshot (truncated)\n")
        parts.append("```")
        parts.append(change.old_snapshot[:4000])
        parts.append("```\n")
    else:
        parts.append("## Prior snapshot\n_None — first time this source has been observed._\n")

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
    """Return (relative_path, content) for each page in applies_to."""
    pages: list[tuple[str, str]] = []
    for rel in change.source.applies_to:
        path = DOCS_ROOT / rel
        if not path.exists():
            continue
        pages.append((f"docs/{rel}", path.read_text()))
    return pages


def call_claude(client: Anthropic, change: SourceChange) -> SourceReport:
    """Ask Claude to analyze the source change and propose edits.

    Caching strategy:
      - System prompt cached at the system block (stable across all sources).
      - Each affected page included as its own user content block, cached
        individually. Re-runs on the same source diff against the same pages
        will hit the cache for everything except the diff itself.
    """
    user_blocks: list[dict] = [
        {"type": "text", "text": build_user_message(change)}
    ]
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
                "format": {"type": "json_schema", "schema": REPORT_SCHEMA},
            },
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
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


def apply_edit(edit: ProposedEdit) -> tuple[bool, str]:
    """Apply one edit. Returns (applied, message)."""
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
    # https://github.com/owner/repo.git or git@github.com:owner/repo.git
    if url.startswith("git@github.com:"):
        url = url.removeprefix("git@github.com:")
    elif "github.com/" in url:
        url = url.split("github.com/", 1)[1]
    return url.removesuffix(".git").strip()


def open_pr(branch: str, title: str, body: str) -> str | None:
    """Open a PR via the GitHub REST API. Returns the PR URL or None on failure."""
    repo = github_repo_slug()
    token = os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        print("[pr] missing GITHUB_REPOSITORY or GITHUB_TOKEN; skipping PR creation")
        return None

    base = os.environ.get("GITHUB_BASE_REF", "main")
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

    # Add the agent label so PRs are filterable.
    if pr_number:
        with httpx.Client(timeout=30.0) as client:
            client.post(
                f"https://api.github.com/repos/{repo}/issues/{pr_number}/labels",
                headers=headers,
                json={"labels": ["agent", "source-monitor"]},
            )
    return pr_url


def build_pr_body(
    reports: list[SourceReport],
    errors: list[tuple[Source, str]],
    applied_messages: list[str],
    skipped_messages: list[str],
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
    lines.append("Generated by `agent/monitor.py` on "
                 f"{datetime.now(timezone.utc).isoformat()}.")
    return "\n".join(lines)


def main(argv: Iterable[str] = ()) -> int:
    sources = load_sources()
    state = load_state()
    print(f"[monitor] loaded {len(sources)} sources; {len(state)} prior state entries")

    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=HTTP_TIMEOUT,
        follow_redirects=True,
    ) as http:
        changes, errors, updated_state = detect_changes(sources, state, http)

    print(f"[monitor] detected {len(changes)} changed sources, {len(errors)} fetch errors")

    if not changes and not errors and updated_state == state:
        print("[monitor] nothing to do")
        return 0

    reports: list[SourceReport] = []
    if changes:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("[monitor] ANTHROPIC_API_KEY not set; cannot analyze source changes")
            return 1
        anthropic_client = Anthropic(api_key=api_key)
        for change in changes:
            print(f"[monitor] analyzing {change.source.id}")
            reports.append(call_claude(anthropic_client, change))

    applied_messages: list[str] = []
    skipped_messages: list[str] = []
    for r in reports:
        for e in r.edits:
            ok, msg = apply_edit(e)
            (applied_messages if ok else skipped_messages).append(msg)

    save_state(updated_state)

    # Stage everything that may have changed. State always changes on a run
    # that touched anything; edits may or may not have changed any docs.
    run_git("add", "agent/state.json")
    if applied_messages:
        run_git("add", "docs/")

    diff = run_git("diff", "--cached", "--name-only")
    if not diff:
        print("[monitor] no changes staged; nothing to commit")
        return 0

    branch = f"agent/source-update-{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M')}"
    run_git("config", "user.email", "noreply@github.com")
    run_git("config", "user.name", "source-monitor[bot]")
    run_git("checkout", "-b", branch)
    commit_msg = (
        f"chore(agent): weekly source check ({len(changes)} changed, "
        f"{len(applied_messages)} edits applied)"
    )
    run_git("commit", "-m", commit_msg)
    run_git("push", "origin", branch)

    pr_title = f"Weekly source check: {len(changes)} change(s) detected"
    pr_body = build_pr_body(reports, errors, applied_messages, skipped_messages)
    pr_url = open_pr(branch, pr_title, pr_body)
    if pr_url:
        print(f"[monitor] opened PR: {pr_url}")
    else:
        print("[monitor] PR not opened (see logs above)")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
