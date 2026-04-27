# Domain spotlight: ABA treatment planning

Applied Behavior Analysis (ABA) is one of the higher-stakes domains for generative-AI clinical decision support. The combination of long, individualized treatment plans, high documentation burden, payer scrutiny, and a contested clinical history makes it both a compelling use case and a particularly demanding one.

This page collects the failure modes that generic clinical-AI guidance misses. Two field-specific guidance documents and two foundational articles on ethical AI use in ABA are essential reading alongside this page; full citations are at the end. They are: the **Council of Autism Service Providers (CASP) Practice Parameters for Artificial Intelligence Use in Applied Behavior Analysis**, the **AI Consortium for ABA (AIC-ABA) Ethical Guidelines for AI in ABA** (2026), Jennings & Cox (2023), and Cox (2025).

## 1. Aversives and outdated practices in the training corpus

Pre-modern ABA literature includes contingencies (slaps, electrical stimulation, prolonged restraint) now widely repudiated by professional standards and largely prohibited. Foundation models trained on broad text corpora will have absorbed this material and will reproduce it without explicit guardrails.

**What to do:**

- **Corpus governance.** RAG corpora should be whitelisted by clinical leadership. Older sources endorsing aversives, escape extinction in distress-inducing forms, and "indistinguishability from peers" framing should be excluded. Current peer-reviewed literature, BACB position statements, and neurodiversity-affirming sources should be included.
- **System prompt prohibitions.** Explicit prohibitions against recommending aversives, prone restraint, "quiet hands," "indistinguishability" goals, and similar. Test that the system actually refuses; don't trust the prompt without evals.
- **Verifier rules.** Block prohibited vocabulary in generated outputs. A second-pass check should fail any plan containing prohibited terms.
- **Red-team for it.** Adversarial prompts that attempt to elicit prohibited recommendations should be in the regression suite.

## 2. Neurodiversity-affirming critique

Critiques from autistic self-advocates and aligned researchers (Sandoval-Norton & Shkedy, Leadbitter et al., ASAN policy work) center on:

- **Masking and camouflaging risks.** Goals that train autistic clients to suppress natural expression for the comfort of neurotypical observers cause documented harm.
- **Autonomy.** The client's preferences and self-determination should drive goal selection.
- **Social validity from the client's perspective.** Not just whether goals were achieved, but whether the client and family experienced them as worthwhile.
- **Functional vs. compliance-oriented framing.** Goals should serve the client's life, not produce visible compliance.

**What to do:**

- Build neurodiversity-affirming framing into the system prompt and few-shot examples.
- Include neurodiversity-affirming sources in the RAG corpus.
- Add a rubric line item for neurodiversity-affirming language in clinical evaluation.
- Recruit autistic perspectives into evaluation panels where possible.

## 3. Cultural validity in goal selection

Goal selection embeds cultural values around independence, eye contact, food, communication, and family structure. Literature drawn from WEIRD samples (Western, Educated, Industrialized, Rich, Democratic) skews recommendations.

**What to do:**

- Cultural validity as an explicit eval rubric line item.
- Diverse rater panels, not just demographically, but linguistically and culturally.
- Cultural responsiveness training built into clinician onboarding for the system.

## 4. Templated plans

The single most likely failure mode of a clinical-LLM plan generator is **plans that look complete but aren't individualized**. Payers (including OIG audits of Medicaid ABA in multiple states) are increasingly attentive to this.

**What to do:**

- Track an **inter-plan similarity metric**. Sample plans across clients and measure n-gram or embedding overlap. Persistently high similarity is a homogenization red flag.
- Penalize templating in evaluation rubrics.
- Verifier checks for client-specific anchors: every plan must reference patient-specific data, not just generic goal-bank language.
- Sample audits by clinical leadership.

## 5. Under-served subpopulations

Several populations are systematically underrepresented in ABA literature and goal banks:

- **Girls and women** with autism (historically under-diagnosed and under-studied).
- **Black and Hispanic children** (disparities in service intensity, age at diagnosis).
- **AAC users and non-speaking clients.**
- **Adolescents and adults** (most ABA research is on early intervention).
- **Clients with co-occurring intellectual disability** at the more profound end.

**What to do:**

- Subgroup evaluation as a standing requirement (see [Bias evaluation](../evaluation/bias.md)).
- Explicit corpus expansion to under-represented populations.
- Don't let aggregate metrics paper over subgroup regressions.

## 6. Supervision and scope-of-practice

Plans are authored by BCBAs under the BACB Ethics Code. RBTs and BCaBAs implement plans under supervision. AI assistance must not blur these lines:

- The BCBA is the author. AI is a tool the BCBA uses.
- RBTs see the signed plan, not the AI draft.
- Supervision documentation reflects the BCBA's actual oversight, not just system logs.

See [Clinician-in-the-loop](../governance/clinician-in-the-loop.md).

## 7. Payer-specific plan elements

Payers (Medicaid, TRICARE, commercial) require specific plan elements: operational definitions, baselines, mastery criteria, generalization criteria, parent training goals, discharge criteria, medical necessity rationale. TRICARE ACD adds structured outcome measures (PDDBI, VABS, SRS-2, PSI/SIPA).

Structured output schemas should map directly to payer requirements; verifier checks should flag missing elements before the clinician sees the draft.

## 8. Mandatory reporting and crisis indicators

Suspected abuse or neglect, severe self-injurious behavior, elopement risk, suicidal ideation in older clients: these have mandatory reporting and escalation paths that are not optional. Generative systems must be tested to ensure they:

- Surface these indicators when present in source data.
- Escalate appropriately.
- Do not bury them in narrative summaries.

This is high-priority red-team material.

## 9. Billing integrity

CPT 97151 (and analogous codes) bills clinician assessment time. AI-generated content is not billable; only the clinician's actual time is. Misrepresenting AI-drafted content as clinician-authored time is a False Claims Act exposure.

Documentation should distinguish, where required:

- AI-drafted content
- Clinician-edited content
- Clinician-authored content

See [Accountability](../governance/accountability.md).

## Further reading

The four sources below are the most direct field-specific guidance and analysis on the responsible use of AI in ABA. Treat them as required reading for clinical leadership and as input to any system design or procurement decision.

- **Council of Autism Service Providers (CASP).** *Practice Parameters for Artificial Intelligence Use in Applied Behavior Analysis.* <https://www.casproviders.org/practice-parameters-for-ai>. Field-level guidance on ethical, regulatory, oversight, and implementation considerations for ABA organizations integrating AI.
- **AI Consortium for ABA (AIC-ABA).** *Ethical Guidelines for AI in ABA.* 2026. <https://www.aiaba.org/guidelines>. Consortium guidelines on responsible and ethical deployment of AI tools within ABA practice.
- **Jennings, A. M., & Cox, D. J. (2023).** Starting the Conversation Around the Ethical Use of Artificial Intelligence in Applied Behavior Analysis. *Behavior Analysis in Practice*, 17(1), 107–122. DOI: [10.1007/s40617-023-00868-z](https://doi.org/10.1007/s40617-023-00868-z). Open access: <https://pmc.ncbi.nlm.nih.gov/articles/PMC10891004/>.
- **Cox, D. J. (2025).** Ethical Behavior Analysis in the Age of Artificial Intelligence (AI): The Importance of Understanding Model Building while Formal AI Literacy Curricula are Developed. *Perspectives on Behavior Science*, 48(3), 621–631. DOI: [10.1007/s40614-025-00459-z](https://doi.org/10.1007/s40614-025-00459-z). PubMed: <https://pubmed.ncbi.nlm.nih.gov/40919363/>.
