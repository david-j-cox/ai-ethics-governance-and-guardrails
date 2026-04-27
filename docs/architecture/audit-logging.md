# Audit, logging & explainability

Logs are clinical infrastructure. They are required by HIPAA, indispensable for evaluation, and the only way to investigate things that go wrong after the fact.

## What every generation should log

- **Request metadata:** timestamp, requesting user (clinician ID), patient ID, request type, calling application, session ID.
- **Model context:** model name, model version, system prompt version, prompt template version, sampling parameters.
- **Inputs:** full prompt as sent to the model, full retrieved context with source document IDs and timestamps.
- **Outputs:** full model output, structured fields, citations.
- **Verifier results:** any second-pass check results, flags, auto-corrections.
- **Downstream actions:** clinician edits (diff), clinician sign-off (timestamp + identity), final committed artifact.
- **Cost and latency:** token counts, wall-clock time, retries.

## Additional logging for agentic systems

If the system is wrapped in a planning loop with tool access or persistent state, the per-generation log above is necessary but not sufficient. See [Agentic systems → Logging and audit for agentic systems](agents.md#logging-and-audit-for-agentic-systems) for the full set. In summary, also log every model call the runtime issued (with full prompt and full output), every tool call the runtime executed (name, parameters, return, latency, errors), every read from and write to persistent state, the identity under which the runtime acted, and every halt or escalation that fired. The audit goal shifts from "reconstruct the generation" to "reconstruct the session," and that reconstruction has to be reviewable, not just present.

## Retention

- HIPAA documentation: minimum **6 years** from creation or last in effect, whichever is later.
- Pediatric records: per state law, often **age of majority + N years**. ABA frequently serves pediatric populations; verify state-by-state.
- Adverse event records: indefinite, or per organizational policy.

Plan storage costs from the start. A high-volume clinical generation system produces gigabytes of logs per day; design retention tiers (hot/warm/cold) accordingly.

## Privacy of logs

Logs contain PHI by definition (they include patient IDs, prompts referencing patients, retrieved patient records). Treat the logging system as ePHI infrastructure: BAA with any third-party log host, encryption at rest and in transit, access controls, audit trails on the logs themselves.

## Why this is also explainability

There is a long-running debate about model interpretability: saliency maps, attention patterns, mechanistic interpretability. For clinical generation, the most useful explainability is operational, not mechanistic:

- "What did the model see?": the prompt and retrieved context.
- "What did it produce?": the raw output.
- "What did the clinician do with it?": edits and sign-off.
- "What was the source for each claim?": citations.

A system that logs these well is explainable in the way clinicians, regulators, and patients actually need.

## Accessibility for clinicians

The clinician should be able to see, for any plan they signed:

- The model's draft, the sources it drew on, and the edits they made.
- The system version (model + prompt + schema) at the time.
- Any verifier flags surfaced and how they were resolved.

This is both a clinical safety feature (the clinician can defend the plan to a payer or in court) and a learning loop (patterns of edits inform prompt iteration).

## Adverse event pipeline

Any clinician override past a threshold, any flagged output, any patient/family complaint, and any incident detected in monitoring should land in an adverse-event log with:

- Timestamp, system version, identifier of the affected generation.
- Description of the issue.
- Resolution and root cause.
- Whether it was a single-instance or systemic issue, and what changed in response.

Review monthly with clinical leadership. This is the feedback loop that prevents repeat harms.
