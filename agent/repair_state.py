"""Self-heal agent/state.json after a botched 3-way merge.

When two monitor PRs both modify state.json and a 3-way merge happens
server-side on GitHub (where custom git merge drivers cannot run), the
resulting file can contain duplicated entries with mangled structure like:

      "...last UUID from new block"
    "last_checked": "2026-05-04T...",   <-- stale leftover from old block
    "seen_ids": [ ... ],
    "url": "..."

This module rebuilds state.json by:
  - splitting the file by top-level source keys (regex on `  "<key>": {`),
  - within each block, taking the newest `last_checked`, the union of all
    `seen_ids` (preserving first-seen order), and the last seen value of
    `url` / `content_hash` / `snapshot`,
  - re-emitting valid JSON.

If the file is already valid, repair() is a no-op (returns False).

The monitor calls repair() before load_state() so a corrupted main branch
recovers automatically on the next weekly run.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TOP_KEY_RE = re.compile(r'^  "([^"]+)": \{$')
LAST_CHECKED_RE = re.compile(r'^\s+"last_checked": "([^"]+)",?\s*$')
URL_RE = re.compile(r'^\s+"url": "([^"]+)"\s*,?\s*$')
CONTENT_HASH_RE = re.compile(r'^\s+"content_hash": "([^"]+)",?\s*$')
SNAPSHOT_RE = re.compile(r'^\s+"snapshot": (.+?),?\s*$')
SEEN_ID_RE = re.compile(r'^\s+"([^"]+)",?\s*$')


def _is_valid_json(path: Path) -> bool:
    try:
        json.loads(path.read_text())
        return True
    except (json.JSONDecodeError, OSError):
        return False


def _rebuild(raw_text: str) -> dict[str, dict]:
    lines = raw_text.splitlines()
    block_starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = TOP_KEY_RE.match(line)
        if m:
            block_starts.append((i, m.group(1)))

    if not block_starts:
        raise ValueError("no top-level source keys found; cannot repair")

    end_idx = max(i for i, l in enumerate(lines) if l == "}")

    result: dict[str, dict] = {}
    for idx, (start, key) in enumerate(block_starts):
        next_start = block_starts[idx + 1][0] if idx + 1 < len(block_starts) else end_idx
        body = lines[start + 1 : next_start]

        last_checked_values: list[str] = []
        url: str | None = None
        content_hash: str | None = None
        snapshot: str | None = None
        seen_ids: dict[str, None] = {}

        for line in body:
            m = LAST_CHECKED_RE.match(line)
            if m:
                last_checked_values.append(m.group(1))
                continue
            m = URL_RE.match(line)
            if m:
                url = m.group(1)
                continue
            m = CONTENT_HASH_RE.match(line)
            if m:
                content_hash = m.group(1)
                continue
            m = SNAPSHOT_RE.match(line)
            if m:
                raw_val = m.group(1).rstrip(",").strip()
                try:
                    snapshot = json.loads(raw_val)
                except json.JSONDecodeError:
                    snapshot = raw_val
                continue
            # Any quoted string at array-item indentation is a seen_id candidate.
            # We tolerate missing brackets/commas because that's the corruption.
            sm = SEEN_ID_RE.match(line)
            if sm:
                val = sm.group(1)
                # Filter out the field-name keys we already matched above.
                if val not in {"last_checked", "url", "content_hash", "snapshot", "seen_ids"}:
                    seen_ids.setdefault(val)

        # If we've already accumulated this key (e.g. merge-driver input is
        # the concatenation of two complete state files), merge into the
        # existing entry rather than overwriting it.
        entry = result.setdefault(key, {})
        if last_checked_values:
            new_lc = max(last_checked_values)
            entry["last_checked"] = max(new_lc, entry["last_checked"]) if "last_checked" in entry else new_lc
        if seen_ids:
            existing = dict.fromkeys(entry.get("seen_ids", []))
            for v in seen_ids:
                existing.setdefault(v)
            entry["seen_ids"] = list(existing.keys())
        if content_hash is not None:
            entry["content_hash"] = content_hash
        if snapshot is not None:
            entry["snapshot"] = snapshot
        if url is not None:
            entry["url"] = url

    return result


def repair(path: Path) -> bool:
    """Repair state.json in place if it is invalid JSON.

    Returns True if a repair was performed, False if the file was already
    valid or did not exist.
    """
    if not path.exists():
        return False
    if _is_valid_json(path):
        return False
    rebuilt = _rebuild(path.read_text())
    path.write_text(json.dumps(rebuilt, indent=2, sort_keys=True) + "\n")
    # Verify
    json.loads(path.read_text())
    return True


def merge_driver(ancestor: Path, current: Path, other: Path) -> int:
    """Custom git merge driver for state.json.

    Git invokes this with three files (ancestor, ours/current, theirs/other)
    and expects the merge result to be written back to `current`. We don't
    care about ancestor: both sides only add/refresh seen_ids and timestamps.
    Concatenating the two sides as if they were the file produced by a
    botched merge and running _rebuild over it does the right thing — newest
    last_checked wins, seen_ids are unioned, latest url/hash/snapshot wins.
    """
    combined = current.read_text() + "\n" + other.read_text()
    try:
        rebuilt = _rebuild(combined)
    except ValueError:
        # Fall back to letting git mark a conflict.
        return 1
    current.write_text(json.dumps(rebuilt, indent=2, sort_keys=True) + "\n")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--merge-driver":
        # Args from git: %O %A %B (ancestor, current, other)
        if len(argv) < 4:
            print("usage: repair_state.py --merge-driver <ancestor> <current> <other>", file=sys.stderr)
            return 2
        return merge_driver(Path(argv[1]), Path(argv[2]), Path(argv[3]))

    path = Path(argv[0]) if argv else Path(__file__).resolve().parent / "state.json"
    if repair(path):
        print(f"[repair_state] rebuilt {path} ({len(json.loads(path.read_text()))} keys)")
    else:
        print(f"[repair_state] {path} already valid; no-op")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
