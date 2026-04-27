# Ongoing monitoring & drift

Pre-deployment evaluation establishes a baseline. Monitoring tells you whether you're still meeting it.

## What to monitor

### Output distribution
- Length, vocabulary diversity, structured-field fill rates.
- Sudden shifts (week-over-week) often indicate prompt regressions, model version changes, or retrieval issues.

### Quality proxies
- **Clinician edit rate:** distribution and trend. A rising edit rate is a quality regression; a falling-to-zero edit rate is a rubber-stamping risk.
- **Time-to-sign:** too short suggests rubber-stamping; too long suggests the draft isn't useful.
- **Override rate:** how often clinicians discard the draft entirely.

### Subgroup performance
- All of the above, broken out by the subgroups defined in [Bias evaluation](bias.md).
- Any subgroup-specific drift is a higher-priority alert than aggregate drift.

### Verifier outputs
- Verifier flag rates by category (missing baseline, missing mastery criterion, prohibited vocabulary, citation gap).
- Increasing flag rates indicate the upstream generation is drifting from spec.

### Operational
- Latency, token cost, error rates.
- Retry rates and reasons.

## Cadence

- **Real-time:** error rates, latency, refusal rates. Page on failure.
- **Daily:** output distribution, verifier flag rates.
- **Weekly:** edit rates, time-to-sign, subgroup snapshots, drift indicators.
- **Monthly:** clinical leadership review of adverse event log, sample of outputs, trend analysis. Document what changed.
- **Quarterly:** external red team (see [Red-teaming](red-team.md)).
- **At every model or prompt version change:** re-run a defined regression eval set. No version change ships without it.

## Drift you can detect, drift you can't

Detectable: distribution shifts, verifier flag rate changes, edit rate changes, retrieval recall changes.

Hard to detect without targeted eval: subtle bias regressions, hallucination on long-tail cases, gradual erosion of citation quality, the system getting "worse at" populations that don't show up often in production.

The hard-to-detect category is why you need both monitoring (cheap, broad) and re-evaluation on a schedule (expensive, deep).

## Adverse event handling

Define what constitutes an adverse event. Examples:

- A generated plan recommends an inappropriate intervention that a clinician catches.
- A retrieval surfaces another patient's data.
- A clinician signs off on an output that later proves harmful.
- A patient or family complaint about AI-involved care.

For each: log, investigate, classify (single-instance vs systemic), document resolution, and feed into the monthly review. Patterns drive system changes.

## Don't treat monitoring as ML monitoring

Standard ML monitoring (latency, error rates, model server health) is necessary but insufficient. Clinical monitoring is about whether the system is still doing the clinical job. Build clinical monitoring with clinical leadership, not just SRE.
