# Principles

The site's recommendations follow from a small number of commitments. Where a recommendation seems opinionated, it traces back to one of these.

## 1. The clinician owns the output

Regardless of how the draft was produced, a credentialed clinician is professionally and legally responsible for what their name is attached to. System design should make it easier, not harder, for them to exercise that responsibility. Rubber-stamping is a design failure, not a user failure.

## 2. Aggregate metrics hide subgroup harm

A model that performs well on average can fail systematically for the people clinical care most needs to serve well. Subgroup evaluation is not optional, and it must be planned before deployment, not retrofitted after.

## 3. Confident text is not the same as correct text

LLMs produce fluent prose with high reliability. Whether that prose is correct is a separate question, and it is the question that matters clinically. Grounding, citation, and structured output are how the system makes correctness checkable; without them, a clinician cannot meaningfully review.

## 4. The hard parts are organizational, not technical

Picking the right model is the easy part. Building the review workflow, the consent process, the incident-response plan, the corpus governance, and the subgroup eval pipeline: those are where the work actually lives. Budget and staff accordingly.

## 5. Logs are clinical infrastructure

Every generation should leave a record sufficient to reconstruct what the model saw, what it said, what the clinician did with it, and when. This is required by HIPAA, useful for evaluation, and the only way to investigate things that go wrong.

## 6. Be specific about what "AI does" and "the clinician does"

Vague language about "AI assistance" creates room for both overclaiming (to leadership and patients) and underclaiming (to regulators and payers). The system's role and the clinician's role should be describable in one sentence each.

## 7. Plan for the system to be wrong

It will be. The interesting design question is not how to prevent every error but how to make the inevitable errors visible, recoverable, and learning material for the next iteration.

## 8. Transparency is a deployment requirement

Patients and caregivers should know AI is involved in their care. Staff should know which parts of their workflow it touches. Reviewers, regulators, and the public should be able to see the system's intended use, limits, and evaluation results. Opacity is not a moat; it is a liability.

## 9. Autonomy is a deployment policy, not a property of the model

When a system is wrapped in a planning loop with tool access and persistent state, it sits somewhere on an autonomy gradient (see [Agentic systems](../architecture/agents.md)). Where it sits is set by the deployment policy: which tools are exposed, which actions require confirmation, what is logged, what triggers a halt. The gradient is a property of the system you build or buy, not a property of the model itself. Default the policy to the lowest level that lets the workflow function. Re-review on a stated cadence. Drift, not the original level, is where most accountability gaps open.

A related discipline: do not describe such systems as "deciding," "trying," or "wanting." They are control loops wrapped around probabilistic text generators. Anthropomorphic language obscures where the failure points actually are, and obscured failure points are not safely supervised.
