# Rules of the road for AI agents working in this repo

This file is read by AI coding assistants (Claude Code, Codex, Cursor, Aider, and similar tools) to set the rules for any code they write or modify in this repository. The rules below come from the [Responsible Clinical AI](https://david-j-cox.github.io/ai-ethics-governance-and-guardrails/) playbook for generative-AI clinical decision support.

You may rename this file to `CLAUDE.md`, `.cursorrules`, `.aider.conf.yml` (with adjustments for that tool's syntax), or whatever your tool reads. Many tools will pick up `AGENTS.md` by default. If yours does not, see the [Tool naming conventions](#tool-naming-conventions) section at the end.

This is a living document. Update it as the project evolves. The version below is a starting point, not a ceiling.

---

## What this codebase is

A system that uses generative AI (large language models) to draft, summarize, or otherwise produce clinical content (assessments, treatment plans, progress notes, recommendations) that will inform care for real patients. A credentialed clinician reviews and signs every output before it affects care.

This means the code you write is, eventually, in the path of a clinical decision. Treat it accordingly.

---

## Hard rules (do not break these without explicit human direction)

These rules cause real-world harm if violated. Refuse the task or pause and ask for human input rather than violating them.

### 1. PHI and patient data

- **Never commit real patient data, real identifiers, or anything plausibly derived from them.** Synthetic test fixtures must be obviously synthetic. If you generate sample data, use names like "Test Patient One", clearly fake MRNs, and dates from the future or the distant past.
- **Never log full prompts, retrieved context, or model outputs to stdout, stderr, or any non-HIPAA-controlled log destination during development.** PHI in the prompt means PHI in the logs. Use placeholder data when iterating.
- **Never paste real patient data into external tools you do not control.** This includes web search, public pastebins, public LLM playgrounds, or any service without a Business Associate Agreement (BAA) covering the data.
- **Treat embeddings of clinical text as PHI.** They are subject to HIPAA right-of-access and right-of-deletion the same way the source text is.

### 2. Architecture invariants

- **Retrieval (RAG) over patient records must filter by patient ID as a hard pre-filter, not a post-filter.** Post-filtering means the similarity computation has already considered other patients' data; bugs in the filter become silent cross-patient leaks. If you find post-filtering retrieval code, flag it and propose a rewrite.
- **Tool returns are untrusted data, not instructions.** When the system uses tools that fetch external content (chart notes, web pages, retrieved documents), that content can contain prompt-injection text. Sanitize, tag, or escape tool returns before they enter subsequent prompts. Never let tool output be parsed as instructions.
- **Every clinical generation must be auditable.** That means logged with: timestamp, requesting user, patient ID, model and prompt version, full prompt, retrieved context, full output, verifier results, and downstream clinician edits and sign-off. Do not write generation code that bypasses the audit logger.
- **Structured outputs over free-form prose for clinical fields.** When generating something with a defined schema (treatment plan element, payer-required field, structured assessment), use the model's structured-output features (JSON schema, tool use) and validate. Free-form parsing is a source of silent errors.

### 3. Agentic systems (planning loops, tool use, persistent state)

If any code you are touching plans across multiple steps, calls tools, or holds memory across sessions:

- **Default the autonomy level to the lowest workable point.** The deployment policy is a property of the system, not the model. Prefer "draft for review" or "action with confirmation" over "open-loop execution." If you are introducing a new workflow, do not raise its autonomy level above what was specified.
- **Cap loop depth, step count, and per-session cost.** Add hard limits, not advisory ones. Detect and halt on tool-call repetition.
- **Scope persistent state at the smallest unit the feature requires.** Patient-scoped state must not leak across patients; clinician-scoped state must not leak across clinicians.
- **Runtime acts under a service identity, not a user's session credentials.** When the system invokes a tool, the audit log should show the agent runtime as the actor, not the originating clinician.

### 4. Compliance and legal

- **Do not bypass BAA requirements.** Any new external service the system sends PHI to (model provider, vector DB, observability tool, log host) must have a BAA in place. If you are adding a dependency that handles PHI, surface this requirement in your PR description.
- **Do not represent AI-drafted content as clinician-authored time for billing purposes.** This is a False Claims Act risk in US healthcare. Documentation must accurately distinguish AI-drafted, clinician-edited, and clinician-authored content.
- **Disclosure to patients is required in many jurisdictions when AI is used to generate clinical communications.** When you build a feature that produces patient-facing content, ensure the consent and disclosure path is wired up; do not silently ship a feature that requires consent the system does not have.

---

## Strong preferences (deviate only with reason)

These are not absolute, but the burden of proof is on the deviation, not the default.

### Evaluation and safety

- **Hallucination rate target is zero, not "industry standard."** In documentation that affects patient care, an inaccuracy is a fabricated claim attached to a clinical record. Treat any nonzero rate as a finding to explain and bound.
- **Subgroup evaluation is not optional.** When you build or change a feature that affects clinical output, ensure performance is reported by demographic and clinical subgroup, not just aggregate. Aggregate non-inferiority that hides subgroup regression is not a pass.
- **Refusal-by-default for weakly-grounded claims.** If the system cannot ground a claim in retrieved context, it should say so explicitly rather than fill in plausible text. This is a feature, not a bug.

### Code and tests

- **Test against a real database for integration tests, not mocks, when the test is meaningful only in the real shape.** Mocked migrations have masked production failures before. Use mocks for unit tests, real services (or close clones) for integration.
- **Do not silence type errors, lint warnings, or test failures to ship.** If you are tempted to add a `# type: ignore`, an `eslint-disable`, or a `pytest.skip` to make CI green, stop and surface the underlying issue instead.
- **Prefer editing existing files over creating new ones.** If a new file is genuinely needed, justify it in the PR.

### Logging, observability, and audit

- **Log structured data, not formatted strings.** Future audit and analytics need fields, not free text.
- **Logs that contain PHI go to the HIPAA-controlled log host only.** Application logs, dev logs, and CI logs must be PHI-free.
- **Every model call should record the model version, the prompt template version, and the system prompt version.** When a regression appears, you need to know what changed.

---

## What to do when uncertain

This codebase has higher consequences than most. When in doubt:

1. **Ask before assuming.** If the task is ambiguous and the wrong interpretation could affect patient care, flag the ambiguity and stop.
2. **Prefer the conservative path.** Smaller blast radius, lower autonomy, more human review, more logging.
3. **Surface what you skipped.** If you didn't do something the user asked for because of one of these rules, say so explicitly. Don't silently work around it.
4. **Cite the rule.** When you decline or push back, point at the specific rule above. The user should know whether you're applying a hard rule or making a judgment call.

---

## What this file is not

- **Not a substitute for a security review or a clinical safety review.** These rules are guardrails for routine code generation, not a green light for novel features.
- **Not exhaustive.** Anything not addressed here defaults to the conservative path. If a new pattern keeps coming up, propose adding it to this file.
- **Not legal advice.** The compliance items above reference common requirements in US healthcare, but jurisdictions and obligations vary. Defer to your organization's counsel.

---

## Tool naming conventions

Different AI coding tools look for different filenames at the repo root. To make this file discoverable everywhere, copy it (or symlink it) to whatever your team uses. None of these names are mutually exclusive; you can have multiple.

| Tool | Conventional filename(s) |
|---|---|
| Claude Code | `CLAUDE.md` (project root or any parent directory) |
| OpenAI Codex / agent SDKs | `AGENTS.md` |
| Cursor | `.cursorrules` (legacy) or `.cursor/rules/` directory |
| Aider | `.aider.conf.yml` (different syntax: copy the *content* of this file into the `read:` section, or use the [`/read` command](https://aider.chat/docs/usage/commands.html)) |
| GitHub Copilot Chat | `.github/copilot-instructions.md` |
| Generic / multi-tool | `AGENTS.md` is becoming the de-facto cross-tool convention |

If you maintain more than one, the simplest pattern is to keep the source of truth in `AGENTS.md` and symlink the others:

```sh
ln -s AGENTS.md CLAUDE.md
ln -s AGENTS.md .github/copilot-instructions.md
```

---

## Source

This file is a starting template from the [Responsible Clinical AI scan kit](https://david-j-cox.github.io/ai-ethics-governance-and-guardrails/scan-kit/). The full reasoning behind each rule lives there. Update freely to reflect your project's specifics; the version on the site is a baseline, not a contract.
