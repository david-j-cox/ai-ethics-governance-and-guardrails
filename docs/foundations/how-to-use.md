# How to use this site

The site is structured so different readers can enter where it's most useful for them.

## If you're a clinical leader (BCBA, MD, NP, psychologist)

Read in this order:

1. [Principles](principles.md): the commitments we'll keep coming back to.
2. [Governance → Clinician-in-the-loop](../governance/clinician-in-the-loop.md) and [What "training the model" actually means](../governance/training-the-model.md): the two pages most likely to change how you talk with your engineering team.
3. [Evaluation → Methodology](../evaluation/methodology.md) and [Bias](../evaluation/bias.md): what you should expect to see before any system is used on a real patient.
4. [Checklists → Red flags](../checklists/red-flags.md): keep this open during vendor demos and internal design reviews.

## If you're an engineer or ML lead

Read in this order:

1. [Principles](principles.md).
2. [Architecture](../architecture/index.md), top to bottom.
3. [Evaluation](../evaluation/index.md), top to bottom.
4. [Governance → Clinician-in-the-loop](../governance/clinician-in-the-loop.md): the workflow you build determines whether the rest of the system is safe.
5. [Reference → Regulatory backdrop](../reference/regulatory.md): at least skim, so you know which constraints are real and which are negotiable.

## If you're a founder, operator, or executive sponsor

Read in this order:

1. [Principles](principles.md).
2. [Governance → Accountability](../governance/accountability.md): where the buck stops.
3. [Checklists → Deployment readiness](../checklists/deployment-readiness.md): what "ready" looks like.
4. Skim the rest. Use the table of contents as a map of the work the team needs to be doing.

## If you're a buyer, licensee, or procurement lead

Read in this order:

1. [Audience → Buying vs. building](audience.md#buying-vs-building): how to translate the rest of the site into procurement questions.
2. [Checklists → Red flags](../checklists/red-flags.md): use this directly as the audit instrument. The vendor answers, in writing, with documentation behind every "yes."
3. [Architecture](../architecture/index.md): each subsection is a thing to ask the vendor to confirm. BAAs, deployment posture, RAG isolation, grounding, structured output, audit logs.
4. [Evaluation → Methodology](../evaluation/methodology.md), [Bias](../evaluation/bias.md), and [Minimum criteria & rollback](../evaluation/minimum-criteria.md): the evidence you should expect to see, the subgroups it should cover, and the thresholds you should require contractually.
5. [Governance → Accountability](../governance/accountability.md) and [Clinician-in-the-loop](../governance/clinician-in-the-loop.md): the operational and contractual questions that decide who is responsible when something goes wrong.

The general rule across all five: documented yes is the bar; verbal yes is not.

## If you're evaluating a vendor or an internal build

Use the [red-flags checklist](../checklists/red-flags.md) as the audit instrument. For each item, ask "show me." Documented yes is the bar; verbal yes is not.

## How to cite or quote

This is a living document. If you cite a page, include the date. Site versioning will be added before public release.
