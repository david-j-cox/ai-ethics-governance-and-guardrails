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

**Stub only.** The scaffolding (config, source list, workflow, entrypoint shape) is here. The actual fetch / diff / LLM-prompt / PR-open logic is left as the next implementation step. Wiring this up requires:

- An Anthropic API key (or other LLM provider) stored as a repo secret.
- A GitHub token with `pull-request: write` scope.
- Decision on whether to run as a GH Action (simplest) or a small server (more control).

The default plan is GH Action — see `.github/workflows/monitor.yml`.

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
