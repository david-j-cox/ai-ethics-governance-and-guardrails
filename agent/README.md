# Source-monitoring agent

A weekly job that watches a curated list of sources for substantive changes and opens **pull requests** with proposed site updates. It never auto-merges. The maintainer reviews and accepts.

This is "eat your own dog food": the site warns that AI-generated content needs human review before it affects anything. So does this site's own content.

## How it works

1. `monitor.py` runs on a weekly schedule (`.github/workflows/monitor.yml`).
2. It loads source definitions from `sources/*.yaml`.
3. For each source: fetch, hash, compare to last-known hash in `state.json`.
4. For changed sources: prompt an LLM to summarize the change and propose markdown edits to the relevant `docs/` page.
5. Open a single PR with all proposed edits, labeled `agent`, with a checklist body.
6. The maintainer reviews, edits, and merges (or closes).

## Status

Implemented. Runs as a GitHub Action on a weekly cron and on manual dispatch (see `.github/workflows/monitor.yml`).

## Setup

Two secrets are required in the repo's GitHub Actions configuration (Settings → Secrets and variables → Actions):

- `ANTHROPIC_API_KEY`: an Anthropic API key. The agent uses Claude Opus 4.7 with adaptive thinking and prompt caching. Most weeks no source has changed, so no LLM calls are made; weeks with changes typically use a few thousand input tokens per changed source.
- `GITHUB_TOKEN`: provided automatically by Actions; no manual setup required. The repo's workflow permissions must allow read/write and PR creation (Settings → Actions → General → Workflow permissions).

No other configuration is needed. The agent commits to a fresh branch (`agent/source-update-YYYY-MM-DD-HHMM`), pushes, and opens a single PR labeled `agent` and `source-monitor`.

## Local dry run

```sh
cd agent
pip install -r requirements.txt
ANTHROPIC_API_KEY=... python monitor.py
```

Without `ANTHROPIC_API_KEY` set, the agent will still fetch and update `state.json` for any source whose hash hasn't changed, but it will exit with code 1 if it detects any changed sources.

## What the agent does on each run

1. Loads source definitions from `sources/*.yaml`.
2. Fetches each source over HTTPS with a 30-second timeout. For `html` sources, runs trafilatura to extract main content. For `link-check` sources, just verifies the URL resolves.
3. Hashes the extracted content. Compares to the last-known hash stored in `state.json`.
4. For changed `html` sources, calls Claude Opus 4.7 once per changed source. The system prompt is cached, and each affected page is sent as a separately-cached content block. Subsequent runs against the same diff are near-free.
5. Claude returns structured JSON: a 2-3 sentence summary and a list of proposed edits (`replace`, `append`, or `no-edit`). Edits are conservative find/replace patches, not rewrites.
6. The agent applies edits where the `find` string is unambiguous; ambiguous or missing matches are reported to the PR body for human attention.
7. Updates `state.json` with new content hashes and timestamps for every source successfully fetched, including unchanged ones.
8. If anything changed, commits to a fresh branch and opens one PR.

Fetch failures are logged and skipped; the next run retries from the same baseline. Network blips don't poison state.

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
