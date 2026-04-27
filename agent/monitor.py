"""Source-monitoring agent — STUB.

Weekly job that:
  1. Loads source definitions from agent/sources/*.yaml
  2. Fetches each source and compares to last-known hash in state.json
  3. For changed sources, prompts an LLM to propose markdown edits to docs/
  4. Opens a single PR with all proposed edits, labeled `agent`

The implementation below is a scaffold. It walks the source list and prints
what it would do. Wiring up real fetch/diff/LLM/PR logic is the next step.

Design constraints (deliberate):
  - PR-only. Never auto-merge. The maintainer is the human in the loop.
  - Small diffs. One source change → one section edit, not a rewrite.
  - Cite the source diff in the PR body.
  - If a source change has no clear analogue in the site, open an issue, not a PR.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = Path(__file__).resolve().parent / "sources"
STATE_PATH = Path(__file__).resolve().parent / "state.json"


@dataclass
class Source:
    id: str
    url: str
    type: str
    cadence: str
    applies_to: list[str]
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


def load_state() -> dict[str, str]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(state: dict[str, str]) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True))


def fetch(source: Source) -> str:
    """Fetch source content. STUB — implement with httpx + appropriate parser."""
    raise NotImplementedError("fetch() not yet implemented")


def hash_content(content: str) -> str:
    import hashlib
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def propose_edits(source: Source, old: str, new: str) -> list[dict]:
    """Call an LLM to propose markdown edits for the affected docs/ pages.

    STUB. The contract:
      - Input: the diff (or summarized diff) between old and new source content,
        plus the current contents of each page in source.applies_to.
      - Output: a list of {"path": str, "patch": str, "rationale": str} entries.
      - If no edit is appropriate, return [] and let the caller open an issue.
    """
    raise NotImplementedError("propose_edits() not yet implemented")


def open_pr(edits: list[dict]) -> str:
    """Open a single PR aggregating all edits. STUB."""
    raise NotImplementedError("open_pr() not yet implemented")


def main(argv: Iterable[str] = ()) -> int:
    sources = load_sources()
    state = load_state()
    print(f"Loaded {len(sources)} sources.")
    for s in sources:
        marker = state.get(s.id, "<none>")
        print(f"  {s.id:30s}  cadence={s.cadence:8s}  last={marker[:12]}  applies_to={s.applies_to}")
    print()
    print("Stub mode: no fetches, no edits, no PRs.")
    print("Implement fetch(), propose_edits(), open_pr() to enable.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
