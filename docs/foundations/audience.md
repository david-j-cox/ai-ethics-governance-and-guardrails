# Who this is for

This site is written for **mixed teams building or buying** generative-AI clinical decision support tools. The same questions matter on both sides of the procurement line, so the same reference can serve both. Specifically:

- **Engineering and ML leads** who own the system architecture (or who are evaluating one) and need to know what "responsible" looks like below the slide-deck level.
- **Clinical leaders** (BCBAs, MDs, NPs, psychologists, allied health) who will sign their name to outputs the system produces, and who need a vocabulary for asking the engineering side, or a vendor, hard questions.
- **Founders and operators** who need to understand the real shape of the work: what is genuinely novel, what is table stakes, and where the risks concentrate.
- **Procurement, legal, and compliance** evaluating internal builds or vendor offerings, who can use the checklists directly as audit and RFP instruments.
- **Buyers and licensees** of clinical-AI products. The architecture, evaluation, governance, and checklist sections double as a structured set of questions to put to any vendor before signing.

## Buying vs. building

If you are buying, treat the site like this:

- The **Architecture** section becomes a checklist of things to confirm with the vendor in writing: BAAs, deployment posture, retrieval isolation, grounding, structured-output guarantees, audit logging.
- The **Evaluation** section becomes the evidence ask. What evals did the vendor actually run, on whose data, with which clinician panel, against what minimums? "We tested it" is not an answer.
- The **Governance** section becomes contract and operations questions. Who is accountable on the vendor side? What are the rollback triggers? Who tells you when something goes wrong?
- The **Checklists** are the procurement instruments. The red-flags audit is meant to be answered by the vendor, in writing, with documentation behind every "yes."

If you are building, the same sections are your design and operations spec.

## Who this is not for (yet)

- **End-user clinicians and patients**. There is a gap in the field for plain-language explainers. We may add a separate track for this; today, the site assumes a builder or buyer audience.
- **Researchers** looking for novel methods. The site curates and applies; it does not propose new techniques.
- **Pure-policy readers**. The regulatory section is backdrop, not the spine.

## Assumptions about you

You are building, buying, or licensing a system that:

- Generates or substantially drafts clinical content (assessments, plans, summaries, recommendations) using a large language model.
- Operates inside a covered entity or business associate relationship, on data that is or will be PHI.
- Has, or will have, a licensed clinician reviewing outputs before they affect care.

If any of those isn't true (for example, you're building a consumer wellness app on de-identified data), most of the recommendations still apply, but some sections (consent, BAAs, BACB-specific sections) will not.
