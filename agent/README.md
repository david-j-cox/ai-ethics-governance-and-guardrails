# Source-monitoring agent

A weekly job that watches a curated list of sources for substantive changes and opens **pull requests** with proposed site updates. It never auto-merges. The maintainer reviews and accepts.

This is "eat your own dog food": the site warns that AI-generated content needs human review before it affects anything. So does this site's own content.

## How it works

1. `monitor.py` runs on a weekly schedule (`.github/workflows/monitor.yml`).
2. It loads source definitions from `sources/*.yaml`.
3. For each source: fetch, hash, compare to last-known hash in `state.json`.
4. For changed sources: prompt an LLM to summarize the change and propose markdown edits to the relevant `docs/` page.
5. Open one PR per proposed edit (`agent/edit-*`, labeled `agent` + `proposed-edit`) so each can be accepted or declined on its own. Separately, open an always-mergeable "bookkeeping" PR that only updates `state.json`.
6. The maintainer skims the executive summary in the run email/issue, then merges the edit PRs to accept, closes them to decline, or pushes to a branch to modify.

## Status

Implemented. Runs as a GitHub Action on a weekly cron and on manual dispatch (see `.github/workflows/monitor.yml`).

## Setup

Two secrets are required in the repo's GitHub Actions configuration (Settings → Secrets and variables → Actions):

- `ANTHROPIC_API_KEY`: an Anthropic API key. The agent uses Claude Opus 4.7 with adaptive thinking and prompt caching. Most weeks no source has changed, so no LLM calls are made; weeks with changes typically use a few thousand input tokens per changed source.
- `GITHUB_TOKEN`: provided automatically by Actions; no manual setup required. The repo's workflow permissions must allow read/write and PR creation (Settings → Actions → General → Workflow permissions).

No other configuration is needed. The agent commits state bookkeeping to a fresh branch (`agent/source-update-YYYY-MM-DD-HHMM`) and opens each proposed doc edit as its own `agent/edit-*` PR. It never auto-merges.

## Local dry run

```sh
cd agent
pip install -r requirements.txt
ANTHROPIC_API_KEY=... python monitor.py
```

Without `ANTHROPIC_API_KEY` set, the agent will still fetch and update `state.json` for any source whose hash hasn't changed, but it will exit with code 1 if it detects any changed sources.

## What the agent does on each run

The agent runs three pipelines per run (source watch, research digest, research-derived edits). They share the fetch/state primitives. State bookkeeping is committed in its own always-mergeable PR; every proposed doc edit gets its own `agent/edit-*` PR so the maintainer can accept or decline each independently. The run email/issue opens with an executive summary listing the proposed edits (with PR links), anything needing human attention, and the notable research items.

### Pipeline A: source watch (`html` and `link-check` sources)

For inertial reference material, regulatory guidance, and provider documentation. Watches a fixed list of URLs for substantive content change.

1. For each source, fetch over HTTPS (30s timeout), extract main content via trafilatura, hash.
2. Compare hash to `state.json`. Unchanged sources are no-ops; only update the last-checked timestamp.
3. For changed `html` sources, call Claude Opus 4.7 once per changed source. The system prompt is cached; each affected page is a separately-cached content block.
4. Claude returns structured JSON: a 2-3 sentence summary plus a list of `replace` / `append` / `no-edit` patches.
5. Apply patches where the `find` string is unambiguous; ambiguous or missing matches are reported under "Needs your attention" for human follow-up.
6. Commit state bookkeeping to a fresh `agent/source-update-*` branch (PR labeled `agent` + `source-monitor`), and open each applied patch as its own `agent/edit-*` PR (labeled `agent` + `proposed-edit`).

### Pipeline B: research digest (`feed` sources)

For research, incidents, and capability announcements. Reads RSS/Atom feeds and triages new entries into a digest.

1. Read each feed via `feedparser`. Cap entries inspected per feed at 30, total per run at 150.
2. Dedupe each entry against the per-feed `seen_ids` set in `state.json`. Entries the agent has seen before are skipped.
3. If any new entries exist, send all of them in one batched call to Claude Opus 4.7 for relevance triage. The system prompt biases toward clinical/behavioral-health relevance and against generic LLM benchmark noise.
4. Claude returns one row per entry: `relevant: true|false` plus a one-line pitch (~30 words) for relevant items.
5. Open a separate `agent/research-digest-*` branch with the maintainer-facing digest as the PR body. The PR proposes no docs edits. It is a pointer ("you should look at these"), not an edit.
6. PR labeled `agent` + `research-digest`.

### Both pipelines

- Update `state.json` (content hashes for watch sources, seen_ids for feeds) on every successful fetch, including for unchanged sources. The state file is committed only in the bookkeeping PR(s), never bundled with a proposed edit — so declining an edit never strands the bookkeeping and the monitor won't re-flag the same source next week.
- Fetch failures are logged and skipped, not fatal. Next run retries from the same baseline.
- A clean week with no changes and no new entries opens zero PRs.
- Neither pipeline ever auto-merges. The maintainer is the human in the loop.

## Source list philosophy

We are *not* tracking every state AI law. The site's regulatory section is backdrop, not the spine. Sources to monitor focus on:

- LLM provider documentation relevant to clinical deployment (HIPAA scope, caching, grounding, structured output)
- Voluntary frameworks (NIST AI RMF, CHAI, WHO)
- ONC HTI rules (federal predictive DSI scope evolves)
- FDA CDS guidance updates
- Curated peer-reviewed work on clinical RAG, hallucination eval, bias eval (rate-limited; we don't want a firehose)
- Major incident reports and credible failure-mode write-ups

See `sources/` for the current list.

## Adding a source

Edit `sources/<topic>.yaml` and add an entry. Each source has:

```yaml
- id: nist-ai-rmf
  url: https://www.nist.gov/itl/ai-risk-management-framework
  type: html              # html | rss | pdf | api
  cadence: weekly         # weekly | monthly
  applies_to:             # which docs/ pages this source can update
    - reference/frameworks.md
  notes: |
    NIST AI RMF + GenAI Profile updates. Watch for new profile pubs.
```

## Operating principles

- **PR, never auto-merge.** Single human reviewer for the whole site.
- **Keep diffs small.** One source change → one section update, not a rewrite.
- **Cite the source change in the PR.** What changed at the source URL, what edit is proposed, and why.
- **Don't invent edits.** If a source change doesn't have a clear analogue in the site's content, the agent should open an issue, not a PR.
