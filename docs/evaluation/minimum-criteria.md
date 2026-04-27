# Minimum criteria and rollback plans

Evaluation produces numbers. Numbers only matter if they connect to decisions. Two decisions in particular: *can we use this system?* and *should we keep using this system?* Both require pre-committed thresholds and a documented rollback path.

## Pre-commit your minimums

Before any evaluation produces a number that someone wants to interpret favorably, write down the thresholds that the system must clear to be deployed and to remain in use. Sign them. Date them. Store them where they can't be quietly revised after the fact.

A reasonable minimum set, adapted to your domain:

- **Reference-based rubric:** non-inferiority to current clinician-authored artifacts on every rubric dimension, with no aggregate-pass-but-subgroup-fail patterns. See [Bias](bias.md).
- **Hallucination eval:** unsupported-claim rate at the floor your eval method can resolve, with a stated target of zero. See [Methodology, Layer 4](methodology.md#layer-4-hallucination-eval).
- **Adversarial set:** 100% correct handling of the safety-critical cases (severe self-injurious behavior, elopement, suspected abuse, custody complications, and any others your domain demands). One miss on this set is one too many.
- **Subgroup performance:** rubric and hallucination metrics within a stated tolerance of the population mean for every subgroup you can measure. Out-of-tolerance subgroups block deployment for that subgroup, not just for the average user.
- **Inter-rater reliability:** rubric ICC ≥ 0.8 (see [Methodology, Layer 1](methodology.md#layer-1-reference-based-clinician-rubrics)). Without this, your other numbers are not load-bearing.
- **Audit completeness:** every output traceable to model version, prompt version, retrieved context, and reviewing clinician. See [Audit, logging & explainability](../architecture/audit-logging.md).

These are minimums to *consider* deployment. They are not a guarantee of fitness. Failing any one of them is disqualifying. Clearing all of them earns you the right to make the deployment argument, not the deployment itself.

## Pre-commit your rollback triggers

A system that meets minimums on launch day can drift, regress on a model update, or fail a population it was never properly tested against. Decide in advance what would cause you to pull access, then write it down:

- **Drift on monitored metrics** beyond a stated tolerance, sustained over a stated window. See [Ongoing monitoring & drift](monitoring.md).
- **Repeated safety-critical failures**: a small number of cases where the system produced output that, if not caught, would have harmed a patient. The threshold for "small" should be one or two, not ten.
- **Subgroup regression**: previously-passing subgroup falls out of tolerance.
- **Hallucination rate regression**: any sustained increase from baseline. A hallucination rate that crept up is a hallucination rate that has to come back down before the system stays online.
- **Vendor change events**: model version change, retraining, or any vendor-side modification you didn't authorize. Rollback by default, re-evaluate, then decide whether to resume.
- **Regulatory or professional-standards change**: a new state law, payer requirement, or professional ethics update that the deployed system does not meet.

## Rollback has to be operationally real

A rollback plan that doesn't exist operationally is a rollback plan in name only. Before deployment, confirm:

- A named owner who can pull the kill switch without a committee meeting.
- A documented procedure that an on-call engineer can execute end-to-end at 2am.
- A communication plan: who tells affected clinicians, in what timeframe, with what guidance for in-flight cases.
- A fallback workflow: clinicians can complete their work without the system. If they can't, you have built a dependency, not a tool, and rollback is theoretical.
- A post-rollback review: documented root cause, documented fix, documented re-evaluation criteria before the system can come back online.

## Routine failure to meet benchmarks is not a tuning problem

If the system meets minimums in eval but routinely fails them in production, the answer is not to lower the bar. The answer is to remove access while you find out why. Sustained underperformance against documented thresholds is a clinical safety event, not a backlog item.

This is uncomfortable because it imposes real cost: training time, license cost, workflow rework, sometimes vendor relationships. The cost of *not* doing it is borne by patients who didn't choose to be the test set. That's not a tradeoff a responsible operator gets to make.

## Make the thresholds visible

Document your minimums and rollback triggers somewhere your governance committee, your clinical leadership, and your compliance partners can find them without asking. Reference them in vendor contracts where applicable. Version them. Review them on a stated cadence.

The point of writing them down is so that the deployment decision and the keep-using-it decision are not made under pressure, in a meeting, by people who would prefer the system to keep working.
