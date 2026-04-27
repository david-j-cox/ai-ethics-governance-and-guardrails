# Evaluation methodology

There is no settled industry standard for evaluating clinical generative AI. The stack below is defensible (used in some form by most credible health-AI shops) and it composes. You don't need all of it on day one; you do need a roadmap to all of it before deployment.

## Layer 1: Reference-based clinician rubrics

A blinded panel of clinicians scores AI-generated outputs against human-authored outputs on a fixed rubric.

- **Panel size:** ≥3 clinicians per item, drawn from outside the build team.
- **Inter-rater reliability:** target ICC ≥ 0.8 on the rubric. If you can't reach that, the rubric is the problem, not the raters.
- **Blinding:** raters should not know which output is AI-generated. Counterbalance presentation order.
- **Rubric dimensions** (adapt to your domain):
    - Clinical appropriateness
    - Individualization (does it reflect this patient, not a template?)
    - Evidence base (are recommended interventions supported?)
    - Completeness against payer/regulatory requirements
    - Safety (does anything in the output put a patient at risk?)
    - Tone and communication (especially for patient-facing content)

## Layer 2: Non-inferiority against current practice

Before deployment, prospectively compare AI-generated outputs to the artifacts your clinicians would have produced without the system, on a held-out case set (≥100 cases for most use cases; more for high-stakes generation).

- The bar is **non-inferiority on the rubric**, not identity. AI-assisted plans don't need to look like human plans; they need to be at least as good.
- Report by subgroup (see [Bias](bias.md)). Aggregate non-inferiority that hides a subgroup regression is not a pass.

## Layer 3: Adversarial / red-team set

A curated set of edge cases the system must handle correctly. For ABA treatment planning these include:

- Severe self-injurious behavior or aggression
- Elopement risk
- Medical complexity
- Custody disputes or unclear guardian authority
- Suspected abuse or neglect
- AAC-using or non-speaking clients
- Clients with co-occurring intellectual disability
- Adolescents and adults (often under-tested)
- Cultural and linguistic diversity

For each, define expected behavior (generation with appropriate framing, refusal with appropriate escalation, or human handoff) and verify.

## Layer 4: Hallucination eval

For a sample of ≥200 outputs, manually trace every clinical claim to a cited source. Report:

- **Unsupported-claim rate** per 1k tokens.
- **Citation accuracy:** when cited, does the source actually support the claim?
- **Numeric integrity:** for outputs containing numbers, are they correct?
- **Negation handling:** are absence-of-evidence and evidence-of-absence distinguished correctly?

### A hallucination rate greater than zero is an ethical problem, not a quality metric

In documentation that affects a patient's care, an inaccuracy is not a defect to be tracked alongside latency and throughput. It is a fabricated claim attached to a clinical record, with the clinician's name on it. Treat the target rate as zero and any nonzero rate as a finding that has to be explained, mitigated, and bounded, not just monitored. "Industry-standard" hallucination rates from general-purpose chat benchmarks are not a defense for misstating something about a real patient.

This framing has design consequences. It pushes you toward refusal-by-default when grounding is weak, toward second-pass verifiers, and toward structured output with mechanical checks (see [Grounding](../architecture/grounding.md) and [Structured output](../architecture/structured-output.md)). It also pushes you toward [clinician-in-the-loop](../governance/clinician-in-the-loop.md) review designed to catch fabrications, not rubber-stamp them.

## Layer 5: Shadow mode

Run the system in production conditions for a defined window without exposing outputs to clinicians. Compare retrospectively:

- What did the system produce?
- What did clinicians actually do?
- Where they agreed, can you trust the system to assist?
- Where they disagreed, who was right?

Shadow mode is the closest you get to a real-world dress rehearsal. Skipping it is a frequent regret.

## What benchmarks don't tell you

Public benchmarks (MedHELM, HealthBench, MedQA, and similar) measure general medical reasoning, not your specific use case. They are useful for model selection and for sanity checks. They are not evaluation. Your eval has to be on your data, your tasks, and your subgroups.

### There are no benchmarks for ABA or behavioral health

Be explicit about this with leadership and procurement. As of this writing, there is no public, peer-reviewed benchmark that measures generative-AI performance on ABA treatment planning, functional assessment summarization, behavior-analytic clinical reasoning, or mental-health documentation in any defensible way. Medical benchmarks do not transfer. Medicine and behavioral health are different domains with different evidence bases, different documentation conventions, different regulatory regimes, and different failure modes. A model that scores well on MedQA tells you nothing about whether it will write a defensible behavior plan or avoid recommending aversives.

Practical consequences:

- A vendor citing medical benchmarks as evidence of behavioral-health competence is making a category error. Push back.
- "We tested it on USMLE-style questions" is not an ABA evaluation. Ask what was tested on actual ABA tasks, by actual BCBAs, with what rubric and what inter-rater reliability.
- Until domain-specific benchmarks exist, your evaluation is the benchmark. Build it carefully, report it transparently, and treat the absence of external comparators as a reason for *more* internal rigor, not less.

## Eval is a system, not a project

The above is not a one-time effort. It is an ongoing capability:

- Eval data should grow as the system encounters new cases.
- Clinician raters should rotate to prevent drift.
- Rubrics should be versioned and audited for clinical relevance.
- Eval results should drive prompt, retrieval, and corpus changes, and re-evaluation after each change.
