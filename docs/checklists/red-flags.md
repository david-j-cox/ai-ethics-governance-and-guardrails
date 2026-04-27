# Red flags audit

Use this checklist as a diagnostic instrument, for vendor evaluations, internal builds, or governance reviews. The bar is **documented yes**; verbal yes from a project sponsor is not enough. For each item, ask "show me."

## Governance

- [ ] Is there a named accountable executive (not just IT or engineering)?
- [ ] Has the malpractice carrier been notified in writing and coverage confirmed?
- [ ] Is there a written AI-use policy referencing applicable professional standards (e.g., BACB Ethics Code), HIPAA, applicable state law, and payer contracts?
- [ ] Is there a documented incident-response plan for AI-related adverse events?
- [ ] Is there a defined rollback path that does not disable clinical operations?

## HIPAA & data

- [ ] BAA in place with model provider, cloud host, and every subprocessor, before any PHI flowed?
- [ ] Zero data retention configured and verified by the vendor in writing?
- [ ] Vector store and prompt logs treated as ePHI with full HIPAA controls?
- [ ] Minimum-necessary scoping enforced at the retrieval layer, not just the application layer?
- [ ] Deletion workflow exists for client data and embedding requests, and has been tested?
- [ ] Vendor-side telemetry disabled or replaced with HIPAA-controlled logging?

## Clinical

- [ ] Every output reviewed and signed by a credentialed clinician who can articulate the rationale?
- [ ] Clinician edit rate above a defined threshold? (Rubber-stamping is the failure mode.)
- [ ] Time-to-sign metric tracked and audited?
- [ ] Source citations on every clinical claim in the output?
- [ ] Adverse event log with monthly clinical leadership review?
- [ ] Tiered review workflow with explicit risk-based triage?
- [ ] Escalation paths from review (disagree, reassign, flag adverse event)?

## Bias & safety

- [ ] Pre-deployment evaluation reported by demographic and clinical subgroup, not just aggregate?
- [ ] Intersectional subgroups defined and reported on?
- [ ] Explicit prohibitions and tested refusals around domain-specific harms (for ABA: aversives, restraint, "indistinguishability" goals)?
- [ ] RAG corpus content-curated and version-controlled by clinical leadership?
- [ ] Quarterly red team by people not on the build team?
- [ ] Inter-plan / output similarity tracked (templating detection)?

## Transparency

- [ ] Patients and caregivers informed at intake and at substantive milestones, with documented assent/consent?
- [ ] Plain-language description of AI use, accessible at relevant reading levels and languages?
- [ ] Opt-out path that actually works operationally?
- [ ] Public-facing description of AI use and limitations (model card / nutrition label)?
- [ ] External claims (marketing, conference talks) reviewed for accuracy?

## Regulatory

- [ ] FDA CDS carve-out criteria documented in writing for the system, with a review cadence to confirm continued applicability?
- [ ] State law compliance reviewed (CA AB 3030, CO AI Act, TX, UT, others as applicable)?
- [ ] Payer contracts reviewed for AI-use restrictions or notification clauses?
- [ ] Billing integrity reviewed (no AI-generated content represented as clinician-authored time)?

## Quality

- [ ] Non-inferiority study against current human-authored outputs, by subgroup, completed and reported before deployment?
- [ ] Drift monitoring with clinical leadership review?
- [ ] Hallucination eval with unsupported-claim and citation-accuracy metrics?
- [ ] Clinician feedback loop with documented response and iteration cadence?
- [ ] Regression eval re-run on every model or prompt version change?

## Agentic systems (if applicable)

If the architecture is a planning loop with tool access or persistent state (including managed platforms like Claude Managed Agents, Gemini Enterprise Agent Platform, or Bedrock Agents), these items apply in addition to those above. See [Agentic systems](../architecture/agents.md).

- [ ] Autonomy policy documented per workflow (suggestion, draft, action with confirmation, action with audit, open-loop), with the lowest workable level chosen by default?
- [ ] Per-tool allowlist and per-tool credential scope documented? (The runtime holds no credentials beyond what each workflow requires.)
- [ ] Hard caps on loop depth, step count, cost, and recursion enforced and tested?
- [ ] Tool returns treated as untrusted data, with prompt-injection defenses tested adversarially?
- [ ] Persistent state scoped at the smallest unit the feature requires (per-patient, per-clinician), with a tested deletion path?
- [ ] Runtime acts under a dedicated service identity, distinct from clinician identity in audit logs, with on-behalf-of boundaries explicit?
- [ ] Every model call, tool call, state read/write, and circuit-breaker firing logged and reviewable?
- [ ] Autonomy-creep review on a stated cadence, with the same governance committee that approved the initial policy?
- [ ] For managed platforms: BAA scope covers planner, tool runtime, persistent state, and platform-side logging? Buyer can pin model versions and is notified before upgrades?

## What this checklist is not

A green checklist does not certify a system as safe. It certifies that a defensible body of work is in place. Safety is established by the work itself, on real data, with real clinicians, on a continuing basis.
