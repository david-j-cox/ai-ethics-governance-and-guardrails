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

## CASP: Practice Parameters for AI Use in ABA

**Council of Autism Service Providers (CASP)**, *Practice Parameters for Artificial Intelligence Use in Applied Behavior Analysis*. <https://www.casproviders.org/practice-parameters-for-ai>.

Field-level guidance for ABA organizations integrating AI tools into clinical workflows. Covers ethical, regulatory, oversight, and implementation considerations specific to autism services and ABA practice. The closest analogue to CHAI's assurance work, but written for the ABA context — including credentialed-clinician accountability, supervision structures, and the realities of ABA documentation and billing.

The most field-specific operational reference available for ABA organizations standing up AI governance.

## AIC-ABA: Ethical Guidelines for AI in ABA

**AI Consortium for ABA (AIC-ABA)**, *Ethical Guidelines for AI in ABA* (2026). <https://www.aiaba.org/guidelines>.

Consortium guidelines on responsible and ethical deployment of AI tools within ABA practice. Complements the CASP parameters: where CASP is oriented toward organizational practice and implementation, AIC-ABA is oriented toward the ethical commitments that should govern AI use across the field.

Read together, these two documents form the de facto field-specific baseline for ABA AI governance, and should be read alongside the BACB Ethics Code rather than as a substitute for it.

## How these compose

- **NIST AI RMF** is the lifecycle scaffolding.
- **CHAI** is the health-specific operationalization.
- **WHO** is the ethical commitments.
- **HTI-1** is the transparency artifact.
- **AMA** is the framing for physician/clinician roles.
- **CASP** and **AIC-ABA** are the ABA field-specific operationalization and ethical commitments.

A defensible governance program references all of them, picks the operational artifacts (model cards, eval reports, risk registers) that map to your context, and maintains them as living documents.
