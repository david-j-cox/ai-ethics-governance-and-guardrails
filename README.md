# Responsible Clinical AI

A builder's blueprint, and a buyer's reference checklist, for teams working with generative-AI clinical decision support. Written for the engineers, clinicians, and leaders who have to make it work in practice.

Live site: <https://responsible-clinical-ai.org/>.

This is a living site. Content is markdown under `docs/`, built with MkDocs Material, deployed to GitHub Pages. A weekly agent watches a curated source list and an RSS feed list, and opens pull requests for the maintainer to review. The agent never merges its own work.

## Local development

```bash
pip install -r requirements.txt
mkdocs serve
```

Open <http://127.0.0.1:8000>.

## Branches

- `main`: the deployed branch. GitHub Pages publishes from it on every push.
- `dev`: the default working branch. Day-to-day edits, source-monitor PRs, and the research-digest PRs target this branch. Promote `dev` to `main` via PR for releases.

## Deploy

Pushes to `main` trigger `.github/workflows/deploy.yml`, which builds the site and publishes to GitHub Pages.

## The weekly agent

`.github/workflows/monitor.yml` runs `agent/monitor.py` on a weekly cron and on manual dispatch. The agent has two pipelines:

- **Source watch.** Fetches a fixed list of HTML pages (regulatory guidance, frameworks, vendor docs, professional-society pages), hashes the extracted content, and asks Claude to propose surgical find/replace edits to affected docs when something substantive changes. Opens an "Source updates" PR with the proposed edits.
- **Research digest.** Reads RSS/Atom feeds (arXiv filtered, behavior journals, JMIR AI, Nature Digital Medicine, AI Incident Database, Anthropic news), dedupes new entries, and asks Claude for a relevance triage with a one-line pitch each. Opens a separate "Research digest" PR whose body is the maintainer-facing pointer list, with no docs edits.

Both pipelines target `dev`. Source-monitor PRs are labeled `agent` + `source-monitor`. Digest PRs are labeled `agent` + `research-digest`. See `agent/README.md` for the full design contract.

## Structure

```
docs/
  index.md                  # landing
  foundations/              # what this is, who it's for, principles
  architecture/             # technical patterns: deployment, RAG, grounding, structured output, agentic systems
  evaluation/               # eval methodology, bias eval, monitoring, minimum criteria & rollback
  governance/               # clinician-in-the-loop, consent, supervision, accountability
  risks/                    # domain-specific failure modes (ABA, others as added)
  reference/                # regulatory + framework backdrop, glossary
  checklists/               # red-flags audit, deployment readiness
  scan-kit/                 # site page describing the downloadable scan kit
agent/
  sources/                  # YAML source definitions (html, link-check, feed)
  monitor.py                # weekly agent entrypoint (source watch + research digest)
  requirements.txt          # agent-only deps; not pulled into the docs build
scan-kit/
  AGENTS.md                 # downloadable rules-of-the-road for AI coding assistants
  CLAUDE.md                 # same content, named for Claude Code
  clinical-ai-audit.md      # downloadable runnable audit prompt
.github/workflows/
  deploy.yml                # GitHub Pages deploy on push to main
  monitor.yml               # weekly source check + digest (opens PRs, never auto-merges)
```

## Scan kit

`scan-kit/` contains files designed to be dropped into other clinical-AI repositories. They are not part of the site build; users download them directly from GitHub raw URLs linked from the [scan kit page](https://david-j-cox.github.io/ai-ethics-governance-and-guardrails/scan-kit/) on the live site.

## Contributing

Currently private. PRs from the agent require human review. When the project goes public, contribution guidelines will live in `CONTRIBUTING.md`.

## License

TBD before public launch.
