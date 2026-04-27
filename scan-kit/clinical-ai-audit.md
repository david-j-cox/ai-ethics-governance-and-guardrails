# Clinical AI repo audit prompt

Paste this whole file into Claude Code, Codex, Cursor's chat, Aider, or any other coding agent that has read access to your repository. Ask the agent to follow the instructions inside.

The agent will scan the repo against the [Responsible Clinical AI](https://david-j-cox.github.io/ai-ethics-governance-and-guardrails/) checklist and produce a per-item findings report.

This is a starting point for a self-audit. It does not replace a security review, a clinical safety review, or a regulatory review. Treat the output as a worklist, not a clearance.

---

## Instructions to the AI agent

You are conducting a self-audit of a generative-AI clinical decision-support codebase against a fixed set of red-flag and deployment-readiness items. Your output should be a structured findings report the maintainer can act on.

### Operating rules

1. **Read, don't write.** Do not modify files during this scan. Only read code, configs, dependencies, workflows, and documentation.
2. **Cite evidence.** For every finding, point to specific files and line numbers, configuration values, or dependency versions. "I think this is missing" is not a finding; "I searched for X across the repo and found no matches" is.
3. **Be conservative on absence.** If you cannot tell from the code whether something exists (e.g., a contract or process that lives outside the repo), say so explicitly under "Cannot determine from repo," do not mark it as a failure.
4. **Distinguish severity.** Each finding is one of:
   - **BLOCKING**: violates a hard rule. Patient safety, PHI handling, billing integrity, BAA scope, or fundamental architecture invariant.
   - **HIGH**: meaningful gap that should be addressed before any new patients are exposed to the system.
   - **MEDIUM**: should be addressed in the current development cycle.
   - **LOW**: hygiene; track and resolve.
   - **INFO**: observation, not a finding (e.g., something is present and looks fine, or is genuinely out of scope for the repo).

### Scan approach

For each checklist section below:

1. State the question.
2. Describe what you searched for, in what files, with what tools (grep, file reads, dependency inspection, workflow inspection).
3. Report what you found.
4. Assign a severity.
5. Recommend a concrete next step.

If a section is genuinely not applicable (e.g., the repo is a shared library, not a deployed service), say so and skip it. Do not invent applicability.

### Output format

For each section, produce a markdown block of this shape:

```
### [Section name]
**Question:** [the question]
**What I checked:** [search strategy and files inspected]
**What I found:** [evidence]
**Severity:** BLOCKING | HIGH | MEDIUM | LOW | INFO | N/A
**Next step:** [concrete recommendation, or "no action"]
```

At the end, produce a **Summary** block listing all BLOCKING and HIGH findings with one-line descriptions and file pointers, ordered by severity.

---

## Checklist

### A. PHI and data handling

1. **Is real or realistic patient data committed to the repo?** Search for files matching `*.csv`, `*.json`, `*.sql`, `*.parquet` under any data, fixtures, samples, or tests directory. Look for plausible names, dates of birth, MRN-shaped strings, ICD codes, or NPI numbers. Synthetic test data should be obviously synthetic ("Test Patient One", future dates, fake MRNs).

2. **Are environment variables for API keys, database credentials, or PHI-handling service tokens committed?** Search for `.env`, `.env.*`, `credentials.*`, `*.pem`, `*.key`, and for hardcoded `sk-`, `pat_`, `eyJ`-prefixed strings in source. Check `.gitignore` for `.env*` exclusions.

3. **Do logs contain PHI or full prompts?** Find logging or print calls in production code paths. Search for patterns like `log.info(prompt)`, `print(messages)`, `logger.debug(retrieved)`. Flag any that emit raw model inputs/outputs to non-HIPAA-controlled sinks (stdout, stderr, ordinary application logs).

### B. Architecture invariants

4. **Is RAG retrieval filtering by patient ID as a hard pre-filter, not a post-filter?** Find vector search or retrieval code (e.g., `pinecone`, `weaviate`, `pgvector`, `qdrant`, `chroma`, `lancedb`, or custom embedding stores). For each, determine whether the patient ID (or tenant/clinic ID) is part of the search filter passed *to* the index, or applied to results *after* search. Post-filtering is a HIGH-or-BLOCKING finding.

5. **Are tool returns sanitized before re-entering the prompt?** If the system uses tools that fetch external content (chart notes, web pages, document retrieval, MCP servers), find where tool results are fed back into the model. Look for any escaping, tagging (`<tool-output>`), or instruction-stripping. Absence of any handling is a HIGH finding.

6. **Is structured output used for clinical fields with a defined schema?** For any code that generates treatment-plan elements, payer-required fields, or structured assessments, check whether it uses the model's structured-output features (JSON schema, tool use, `output_config.format`) or relies on free-form parsing. Free-form parsing of structured clinical content is a HIGH finding.

7. **Is there an audit logger that records every clinical generation with the required fields?** Look for code that logs model calls. Verify it records timestamp, requesting user, patient ID, model name and version, prompt template version, system prompt version, full prompt, retrieved context with source IDs, full output, verifier results, and downstream clinician edits and sign-off. Missing fields are MEDIUM-to-HIGH depending on which fields.

### C. Agentic systems (if applicable)

If the system has any of: a planning loop, tool-use beyond a single turn, persistent state across sessions, or runs on a managed agent platform (Claude Managed Agents, Gemini Enterprise Agent Platform, Bedrock Agents):

8. **Is the autonomy level documented per workflow?** Find the policy for each agentic workflow. Verify it is the lowest level that lets the workflow function. "Open-loop execution" or "fully autonomous" for clinical workflows is a BLOCKING finding unless explicitly justified with audit infrastructure.

9. **Are there hard caps on loop depth, step count, cost, and recursion?** Find the runtime configuration. Caps must be hard, not advisory. Missing caps are HIGH.

10. **Is per-tool credential scope documented and enforced?** Look for the tool definition and credential setup. The drafting workflow should not hold credentials to the billing system, etc.

11. **Is persistent state scoped at the smallest unit the feature requires?** Verify per-patient state cannot leak across patients, per-clinician state cannot leak across clinicians.

12. **Does the runtime act under a service identity, not the originating clinician's session?** Check tool authentication. Audit logs should show the agent runtime, not the clinician, as the actor.

### D. Compliance and external services

13. **Does any external service receive PHI without a BAA in place?** List all external service dependencies (model providers, vector DBs, observability, log hosts, email, analytics, error trackers like Sentry). For each, note whether the repo contains evidence of a BAA (a BAA reference document, an enterprise account configuration, a `BAA.md`, etc.). Absence of evidence is "Cannot determine from repo" unless a BAA is clearly required and clearly missing.

14. **Is there evidence of a zero-data-retention configuration with the model provider?** Search for ZDR-related configuration, region pinning, no-logging flags, or comments referencing them. ZDR is required for HIPAA-aligned model API usage.

15. **Does the system distinguish AI-drafted, clinician-edited, and clinician-authored content in stored documentation?** Find the database schema or persistence layer for clinical artifacts. There should be fields capturing authorship lineage. Absence is HIGH (False Claims Act exposure if AI content is billed as clinician-authored time).

### E. Evaluation and safety infrastructure

16. **Is there a tracked evaluation suite with subgroup reporting?** Look for an `evals/`, `evaluation/`, `eval/`, or similar directory. Check whether eval results are stored, versioned, and reported by demographic and clinical subgroup, not just aggregate.

17. **Is there a hallucination eval with unsupported-claim and citation-accuracy metrics?** If the system makes clinical claims, there should be an eval that traces every claim to a cited source. Absence is HIGH if the system is anywhere near deployment.

18. **Are there pre-committed minimum thresholds and rollback triggers?** Look for documentation, runbook, or configuration that names: minimum eval scores to deploy, drift tolerances, rollback conditions, and a documented kill-switch procedure. Absence is MEDIUM-to-HIGH depending on deployment proximity.

### F. Code and CI hygiene

19. **Are tests skipped, type errors silenced, or lint warnings disabled in production paths?** Search for `pytest.skip`, `xfail`, `# type: ignore`, `# noqa`, `eslint-disable`, `@SuppressWarnings`. Each should have a justifying comment. Unjustified silencing in production code is LOW-to-MEDIUM.

20. **Do CI workflows run the full eval suite on every model or prompt-template change?** Inspect `.github/workflows/`, CircleCI, or other CI configs. Eval-on-prompt-change is a strong sign; absence means regressions can ship invisibly.

21. **Are dependencies pinned and audited?** Check for lockfiles (`poetry.lock`, `uv.lock`, `package-lock.json`, `pnpm-lock.yaml`) and dependency-vulnerability scanning (Dependabot, Renovate, `pip-audit`, `npm audit` in CI).

22. **Is secret scanning enabled?** Check for GitHub secret scanning (default for public repos; settings page for private), `gitleaks` or `trufflehog` in CI, or pre-commit hooks for secrets.

### G. Disclosure and consent

23. **If the system produces patient-facing content, is the disclosure path wired up in code?** Find the patient-communication features. Verify there is code that records or surfaces AI-involvement disclosure when required (CA AB 3030 and similar state laws). Missing disclosure on patient-facing AI output is a BLOCKING-to-HIGH finding depending on jurisdiction.

24. **Is there a documented opt-out path for patients who decline AI involvement?** Look for opt-out flags in the patient/case data model and code that respects them.

---

## After the scan

Once you've produced the findings report:

1. **List BLOCKING items first.** These are the conversations to have with leadership today.
2. **For each HIGH finding, propose the smallest concrete next change** (a specific file to add, a specific function to refactor, a specific contract clause to verify).
3. **Note the limitations of this scan.** What you could not determine from the repo. Where a human review is required.
4. **Do not produce code edits as part of this report.** This is a diagnostic pass. Edits come later, with human review of each finding.

---

## Source

This audit prompt comes from the [Responsible Clinical AI scan kit](https://david-j-cox.github.io/ai-ethics-governance-and-guardrails/scan-kit/). The reasoning behind each item is documented on the site. Modify the checklist to fit your project's specifics; the version above is a baseline.
