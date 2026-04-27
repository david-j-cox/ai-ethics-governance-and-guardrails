# Deployment readiness

Before the first real patient is affected by your system, you should be able to check every box below. If you can't, you're not ready, and the right move is to delay, not to ship and patch.

## Contracts and infrastructure

- [ ] BAA with model provider, executed and current.
- [ ] BAA with cloud host, executed and current.
- [ ] BAAs with all subprocessors (vector DB, observability, fine-tuning vendors), executed and current.
- [ ] Zero data retention confirmed in writing.
- [ ] Data residency pinned to required region.
- [ ] Vendor incident notification timelines specified and acceptable.
- [ ] Cyber and malpractice insurance reviewed and confirmed for AI-related risk.

## System

- [ ] Model and version pinned (no "latest" aliases in production).
- [ ] Prompt templates versioned in source control.
- [ ] Structured output schemas versioned and documented.
- [ ] Retrieval pipeline tested for cross-tenant and cross-patient isolation.
- [ ] Logging captures every required field (see [Audit, logging & explainability](../architecture/audit-logging.md)).
- [ ] Log retention configured per HIPAA and state pediatric requirements.
- [ ] Verifier pass implemented and tested.

## Evaluation

- [ ] Reference-based clinician rubric defined, with ICC ≥ 0.7 demonstrated on a pilot set.
- [ ] Non-inferiority study against current human-authored outputs completed and reported.
- [ ] Subgroup evaluation completed and reported, including intersectional slices.
- [ ] Adversarial / red-team set defined and run; findings triaged and addressed.
- [ ] Hallucination eval completed; unsupported-claim and citation-accuracy rates documented.
- [ ] Shadow mode completed for the planned duration.
- [ ] Regression eval set defined for ongoing use.

## Governance

- [ ] Named accountable executive identified.
- [ ] Written AI-use policy approved by clinical and legal leadership.
- [ ] Incident-response plan documented and tabletop-tested.
- [ ] Rollback path tested.
- [ ] Adverse event log and monthly review process in place.
- [ ] Quarterly red-team cadence scheduled with external reviewers.

## Clinical workflow

- [ ] Tiered review design implemented with risk-based triage.
- [ ] Sign-off requires an explicit action; no auto-progression.
- [ ] Edit rate, time-to-sign, and override rate dashboards live.
- [ ] Clinician training completed for every clinician using the system.
- [ ] Escalation paths from review tested.

## Patient and caregiver communication

- [ ] Plain-language consent materials prepared and reviewed for reading level and translation.
- [ ] Opt-out workflow tested end-to-end.
- [ ] Front-line staff trained to handle questions and opt-outs.

## External communication

- [ ] Model card / nutrition label published or ready to publish.
- [ ] Marketing claims reviewed for accuracy.
- [ ] Public statements approved through a documented review process.

## What "ready" doesn't mean

It doesn't mean the system is perfect. It means the system is defensible, monitored, and rollback-capable. Errors will happen post-deployment. Readiness is the capacity to detect, investigate, and respond to them.
