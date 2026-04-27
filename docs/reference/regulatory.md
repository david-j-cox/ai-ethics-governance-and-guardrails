# Regulatory backdrop

A working orientation, not legal advice. Verify current scope and applicability with counsel before relying on any item here.

## HIPAA

The two rules that matter most for clinical-LLM systems:

- **Privacy Rule** (45 CFR Part 164 Subpart E): what is PHI, who can use and disclose it, the **minimum necessary** standard.
- **Security Rule** (45 CFR Part 164 Subpart C): administrative, physical, and technical safeguards including **audit controls** (§164.312(b)).

Key provisions for AI systems:

- **Business Associate Agreement (45 CFR §164.504(e)).** Required with the model provider, cloud host, and every subprocessor before PHI flows.
- **Minimum necessary (§164.502(b), §164.514(d)).** Retrieval and prompt context scoped to what's actually needed.
- **Audit controls (§164.312(b)).** Logs sufficient to reconstruct what happened.
- **Right of access and deletion.** Patients can request access to their PHI and, in some cases, deletion. Embeddings derived from their data are within scope.

HHS OCR has not issued an AI-specific HIPAA rule. Existing HIPAA obligations apply in full to AI systems handling PHI.

## FDA: Clinical Decision Support carve-out

Under 21st Century Cures Act §3060 and FDA's 2022 final guidance on Clinical Decision Support Software, software that supports clinical decisions is not regulated as a device if **all four** conditions are met:

1. Not intended to acquire/process medical images or in-vitro diagnostic data or signal-acquisition pattern data.
2. Intended to display, analyze, or print medical information about a patient.
3. Intended to support or provide recommendations to a healthcare professional.
4. Intended to enable the HCP to **independently review the basis** for the recommendations and not rely primarily on them for clinical decisions.

A treatment-plan generator that drafts plans for a credentialed clinician's substantive review and shows its reasoning typically qualifies for the carve-out. Auto-finalizing without meaningful review, or marketing the system as replacing clinical judgment, can push it into device territory.

Document the carve-out reasoning in writing; review periodically as the system evolves.

## State AI laws relevant to healthcare

State-level AI legislation moves fast enough that any list this site maintains will be out of date by the time you read it. Rather than try to keep an in-house tracker current, lean on the dedicated trackers that do this work professionally:

- **NCSL AI legislation tracker** (National Conference of State Legislatures): <https://www.ncsl.org/technology-and-communication/artificial-intelligence-2024-legislation>. Bill-level coverage, state-by-state, updated regularly. Best starting point for orientation.
- **Husch Blackwell AI Watch:** <https://www.huschblackwell.com/2024-state-ai-laws-and-policies>. Annotated tracker of enacted state AI laws and policies, with healthcare-relevant items called out. Useful for compliance scoping.
- **Manatt Health Strategies AI tracker:** specialized analysis on healthcare-AI legislation and regulatory action; check current Manatt publications for the latest.

A non-exhaustive snapshot of healthcare-relevant state laws active in early 2026, useful only as an orientation to the kinds of obligations to expect:

- **California AB 3030** (eff. Jan 2025): disclosure when GenAI is used to generate written or verbal communications about a patient's clinical info; carve-out for content reviewed by a licensed/certified HCP.
- **California SB 1120** (eff. Jan 2025): utilization management decisions involving medical necessity must be made by a licensed clinician, not AI alone.
- **Colorado AI Act** (SB 24-205): duties of care and impact assessments for high-risk AI in healthcare.
- **Texas, Utah, Illinois:** varying disclosure and risk-assessment requirements.

Always verify current effective dates and applicability scope against the trackers above and with counsel. Treat this section as a pointer, not a source of truth.

## Payer requirements

Medicaid (state-by-state), TRICARE, and commercial payers have specific requirements for treatment plan content, clinician authorship, and medical necessity documentation.

- **Medicaid:** Requirements vary by state. Many states publish detailed BHT (behavioral health treatment) policy manuals.
- **TRICARE Autism Care Demonstration (ACD):** Structured outcome measures (PDDBI, VABS, SRS-2, PSI/SIPA) at intake and reauth; specific plan format.
- **Commercial:** Optum, Magellan, Aetna, Anthem, and others publish autism/ABA clinical policies with required plan elements and utilization management criteria.

For AI systems: payer requirements drive what your structured output schema must contain. Compliance is a generation-time concern, not just an audit-time concern.

## Professional standards (ABA-specific)

- **BACB Ethics Code for Behavior Analysts** (eff. 2022): applies to all credentialed behavior analysts. No AI-specific section yet, but existing standards on competence, technology, supervision, documentation, and effective treatment apply in full. The credentialed analyst is responsible for any plan bearing their name regardless of tools used.
- **State licensure acts:** most incorporate the BACB Code by reference.
- **BHCOE accreditation:** many ABA organizations are accredited by BHCOE; standards on documentation, supervision, and quality improvement apply.

## Billing integrity (US)

CPT 97151 (assessment) and analogous codes bill clinician time. Misrepresenting AI-drafted content as fully clinician-authored time is a False Claims Act risk. Documentation should reflect actual clinician activity.
