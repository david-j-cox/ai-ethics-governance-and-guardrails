# Responsible Clinical AI

A builder's blueprint for teams designing generative-AI clinical decision support — written for the engineers, clinicians, and leaders who have to make it work in practice.

This is a living site. Content is markdown under `docs/`, built with MkDocs Material, deployed to GitHub Pages. A scheduled agent watches a curated source list and opens pull requests when something changes; a human (the maintainer) reviews and merges.

## Local development

```bash
pip install -r requirements.txt
mkdocs serve
```

Open <http://127.0.0.1:8000>.

## Deploy

Pushes to `main` trigger `.github/workflows/deploy.yml`, which builds and publishes to GitHub Pages.

## Structure

```
docs/
  index.md                  # landing
  foundations/              # what this is, who it's for, principles
  architecture/             # technical patterns: deployment, RAG, grounding, structured output
  evaluation/               # eval methodology, bias eval, monitoring
  governance/               # clinician-in-the-loop, consent, supervision, accountability
  risks/                    # domain-specific failure modes (ABA, others as added)
  reference/                # regulatory + framework backdrop, glossary
  checklists/               # red-flags audit, deployment readiness
agent/
  sources/                  # YAML source definitions the monitor watches
  monitor.py                # scheduled agent entrypoint
.github/workflows/
  deploy.yml                # GitHub Pages deploy
  monitor.yml               # weekly source check (opens PRs, never auto-merges)
```

## Contributing

Right now this is a private project. PRs from the source-monitoring agent require human review. When the project goes public, contribution guidelines will live in `CONTRIBUTING.md`.

## License

TBD before public launch.
