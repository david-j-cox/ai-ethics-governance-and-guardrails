# Scan kit

A pair of downloadable files you can drop into your own clinical-AI repository. They turn the principles, architecture, and checklists on this site into something your AI coding assistant and your audit process can actually use.

The kit is tool-agnostic. Both files work with Claude Code, OpenAI Codex, Cursor, Aider, GitHub Copilot, or any agent that reads repository context. Naming conventions differ between tools; instructions for each are in the files themselves.

## What's in the kit

### 1. AGENTS.md / CLAUDE.md: rules of the road

A single markdown file you place at the root of your repo. AI coding assistants read it before writing or modifying code in the repo, and it sets hard rules they won't violate without explicit human direction.

The rules cover:

- PHI and patient data handling
- Architecture invariants (RAG patient-ID filtering, treating tool returns as untrusted data, audit logging, structured output)
- Agentic systems (autonomy level, loop caps, state scoping, runtime identity)
- Compliance basics (BAA scope, billing integrity, disclosure)
- Strong preferences for evaluation, code, and observability
- What to do when uncertain

The same content ships under two filenames so you can match whichever convention your tool expects:

- **[Download `AGENTS.md`](https://raw.githubusercontent.com/david-j-cox/ai-ethics-governance-and-guardrails/main/scan-kit/AGENTS.md){:download="AGENTS.md"}**, the cross-tool de facto convention.
- **[Download `CLAUDE.md`](https://raw.githubusercontent.com/david-j-cox/ai-ethics-governance-and-guardrails/main/scan-kit/CLAUDE.md){:download="CLAUDE.md"}**, the convention Claude Code reads.

You can keep one or both. If you keep both, symlink one to the other so they don't drift.

### 2. clinical-ai-audit.md: runnable audit prompt

A markdown file you paste into your AI coding assistant's chat with the instruction "follow the instructions in this file." The agent then scans your repository against the [Responsible Clinical AI](../checklists/red-flags.md) checklist and produces a structured findings report with severity levels, evidence, and recommended next steps.

The audit covers:

- PHI and data handling (committed data, secrets in source, PHI in logs)
- Architecture invariants (RAG isolation, tool-return sanitization, structured output, audit logging)
- Agentic systems (if applicable)
- Compliance and external services (BAA scope evidence, ZDR configuration, authorship lineage)
- Evaluation and safety infrastructure (subgroup reporting, hallucination eval, minimum thresholds, rollback)
- Code and CI hygiene (test skips, type-error silencing, dependency pinning, secret scanning)
- Disclosure and consent paths

Output is a per-section findings report with severity tags (BLOCKING / HIGH / MEDIUM / LOW / INFO / N/A), file pointers, and a prioritized summary.

- **[Download `clinical-ai-audit.md`](https://raw.githubusercontent.com/david-j-cox/ai-ethics-governance-and-guardrails/main/scan-kit/clinical-ai-audit.md){:download="clinical-ai-audit.md"}**

## How to use the kit

### Day one of a project

1. Download `AGENTS.md` (and optionally `CLAUDE.md`) and commit it to the root of your repo. Edit it to reflect your project's specifics, but keep the hard rules.
2. Run the audit prompt once to get a baseline findings report. Most early findings will be "Cannot determine from repo" or LOW; that's expected.

### As the project grows

3. Re-run the audit on a stated cadence (monthly during active development, quarterly thereafter, and always before any change in deployment scope).
4. Update `AGENTS.md` whenever a new pattern recurs. If you keep correcting your AI coding assistant on the same point, write the rule down once.

### Before any deployment

5. Run the audit once. Triage every BLOCKING and HIGH finding. Do not deploy with open BLOCKINGs.
6. Cross-reference the findings against the site's [deployment readiness checklist](../checklists/deployment-readiness.md).

## What the kit is not

- **Not a substitute for security review, clinical safety review, or regulatory review.** It catches a class of common mistakes; it does not certify a system as safe.
- **Not exhaustive.** The lists are deliberately scoped to issues that show up in code or repo configuration. Many important questions (clinician training, governance committees, malpractice carrier notification) live outside the repo and are not in the audit's scope.
- **Not a replacement for the rest of this site.** The reasoning behind each rule and audit item is on the site. When the kit says "treat tool returns as untrusted data," the [Agentic systems](../architecture/agents.md) page explains why and how.

## Tool naming conventions, briefly

| Tool | Filename it reads |
|---|---|
| Claude Code | `CLAUDE.md` (project root or any parent) |
| OpenAI Codex / agent SDKs | `AGENTS.md` |
| Cursor | `.cursorrules` (legacy) or `.cursor/rules/` directory |
| Aider | use `/read` to load `AGENTS.md` into context, or configure via `.aider.conf.yml` |
| GitHub Copilot Chat | `.github/copilot-instructions.md` |
| Generic / multi-tool | `AGENTS.md` is the de facto cross-tool convention |

The full table and copy-paste symlink commands are in the downloaded `AGENTS.md` itself.

## Support this work

The scan kit, the audit prompt, and the rest of this site are maintained by one person and kept free. If the kit saves you a review cycle or catches a finding before it ships, consider chipping in:

- [Sponsor on GitHub](https://github.com/sponsors/david-j-cox) — recurring or one-time, all tiers welcome.
- [Tip on Ko-fi](https://ko-fi.com/davidjcox) — one-time tip, no account needed.

Funds go to the time it takes to keep the site current as the regulatory and tooling landscape shifts.

## Contributing back

If you run the kit and find a rule that should be tightened, a finding category that's missing, or a tool whose convention should be added, the site is open to suggestions. The repo is at <https://github.com/david-j-cox/ai-ethics-governance-and-guardrails>.
