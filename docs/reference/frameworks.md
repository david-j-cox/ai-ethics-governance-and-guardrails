# Frameworks & standards

The voluntary frameworks worth knowing. None are legally binding on most clinical-AI systems today; many are the de facto industry baseline and are converging into binding requirements over time.

## NIST AI Risk Management Framework

**NIST AI RMF 1.0** (2023) and the **Generative AI Profile** (NIST AI 600-1, 2024).

Four core functions:

- **Govern:** policies, accountability, roles, risk tolerance, third-party risk, incident response.
- **Map:** context, intended use, foreseeable misuse, impacted stakeholders.
- **Measure:** quantitative and qualitative evaluation across trustworthiness characteristics (validity, reliability, safety, security, explainability, privacy, fairness, accountability).
- **Manage:** risk treatment, monitoring, communication.

The GenAI Profile calls out specific risks (confabulation, data privacy, info integrity, value-chain risks) and maps them to actions.

Most under-implemented function in healthcare AI shops: **Govern**.

## Coalition for Health AI (CHAI)

CHAI's **Assurance Standards Guide** is the closest thing to an industry-baseline practical reference for documenting and evaluating health AI. Notable for:

- **Applied Model Card:** the format most credible health-AI shops are converging on.
- **Fairness** guidance with explicit subgroup performance reporting expectations.
- **Lifecycle approach:** documentation, evaluation, and governance from design through retirement.

## WHO

- **Ethics and Governance of AI for Health** (2021), six core principles: protect autonomy; promote human well-being/safety/public interest; ensure transparency/explainability; foster responsibility/accountability; ensure inclusiveness/equity; promote responsive and sustainable AI.
- **Ethics and Governance of AI for Health: Guidance on Large Multi-Modal Models** (2024), explicitly LLM-focused. Addresses risks of generated clinical content, liability, and labor implications.

International, but informative for US contexts; the principles translate.

## ONC HTI-1: Decision Support Intervention transparency

**45 CFR §170.315(b)(11)**, finalized in the HTI-1 rule (effective Jan 2025 for predictive DSIs). Requires certified EHRs to make available source attribute information for decision support models: intended use, intended users, training data, fairness assessment, validation, ongoing maintenance.

Directly binds only certified health IT (mostly EHRs). For non-EHR systems, this is the closest federal analogue to a "model card" requirement and is a sensible voluntary standard to adopt.

## AMA: Augmented Intelligence Principles

The American Medical Association's principles emphasize:

- AI as augmentation, not replacement, of clinical judgment.
- Physician oversight of AI-driven recommendations.
- Transparent training data and validation.
- Equitable design and deployment.
- Liability frameworks that don't unfairly transfer risk to clinicians.

Useful framing for organizational AI policies.

## Joint Commission / CHAI Responsible AI Certification

A forthcoming voluntary certification (announced 2024) for organizations deploying health AI. Watch for it; if your accreditor is The Joint Commission, alignment will eventually matter.

ABA organizations more often accredited by **BHCOE**. No AI-specific standards from BHCOE as of early 2026, but their existing standards on documentation, supervision, and QI apply.

## How these compose

- **NIST AI RMF** is the lifecycle scaffolding.
- **CHAI** is the health-specific operationalization.
- **WHO** is the ethical commitments.
- **HTI-1** is the transparency artifact.
- **AMA** is the framing for physician/clinician roles.

A defensible governance program references all of them, picks the operational artifacts (model cards, eval reports, risk registers) that map to your context, and maintains them as living documents.
