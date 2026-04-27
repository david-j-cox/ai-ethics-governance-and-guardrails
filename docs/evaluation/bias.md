# Bias & subgroup evaluation

Aggregate metrics hide subgroup harm. A model that performs well on average can fail systematically for the populations clinical care most needs to serve well, and those failures are often the ones with the highest moral and legal stakes.

This is not a "fairness" problem to be solved by a single metric. It is a discipline of asking, repeatedly: who is this working for, who is it not working for, and what are we doing about it?

## Subgroups to evaluate

The right set depends on the population you serve. A reasonable default for behavioral health and developmental disability use cases:

- **Race and ethnicity** (per OMB categories or finer-grained as data allows)
- **Sex assigned at birth** and **gender identity**
- **Age band** (early intervention, school-age, adolescent, adult)
- **Primary language**
- **Communication modality** (vocal, AAC, multimodal, non-speaking)
- **Co-occurring intellectual disability**
- **Insurance type** (Medicaid, TRICARE, commercial, self-pay), a proxy for systemic disparities
- **Geography** (urban, rural)

## Intersectional slices matter

Single-axis bias evaluation routinely misses harm at intersections: Black girls, Spanish-speaking adolescents using AAC, rural Medicaid clients with co-occurring ID. Pre-define the intersections that matter clinically and report on them.

## Metrics to report by subgroup

The same metrics you report in aggregate, broken out:

- **Plan completeness** rate
- **Clinical appropriateness** (rubric scores)
- **Hallucination rate**
- **Refusal / under-coverage rate:** does the system disproportionately fail to generate substantive output for some subgroups?
- **Citation density:** are some subgroups under-served by the retrieval corpus?
- **Edit rate by subgroup:** do clinicians edit AI outputs more heavily for some populations? That's a signal.

## Sources of bias to investigate

- **Training data of the foundation model.** You can't audit it, but you can probe for symptoms.
- **Your retrieval corpus.** If your protocols, goal banks, and reference literature systematically under-represent some populations, the system will too.
- **Your prompt templates.** Implicit assumptions in templates ("the client will," "the parent will") may not generalize across family structures, communication modalities, or cultures.
- **Your evaluation panel.** A homogeneous rater panel will miss what they're not positioned to see. Recruit diversely.

## What to do about findings

Findings without action are theater.

- **Document the disparity** with effect size and confidence interval, not just direction.
- **Investigate the cause:** corpus, prompt, retrieval, model, eval rater pool.
- **Intervene where you can:** corpus expansion, prompt redesign, targeted RAG, post-generation checks.
- **Decide what's in scope and what's a deployment limit.** Sometimes the right answer is "this system is not yet ready to serve population X; we are excluding that case until it is."
- **Re-evaluate** after intervention. Verify the intervention helped and didn't regress other subgroups.

## Cultural validity

Beyond demographic fairness: do the recommendations make sense across cultural contexts? Goals embed values around independence, eye contact, food, and family structure. Literature drawn from WEIRD samples skews recommendations.

- Rater panels with cultural diversity.
- A "cultural validity" rubric line item.
- Clinical sign-off by clinicians familiar with the populations served.

## The trap of "neutral" defaults

A system that defaults to the cultural and clinical assumptions of its build team is not neutral; it is biased toward that team. Make defaults explicit and contestable.
