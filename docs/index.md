# Responsible Clinical AI

A builder's blueprint, and a buyer's reference checklist, for teams working with **generative-AI clinical decision support**. Written for the engineers, clinicians, and leaders who have to make it work in practice.

This site is opinionated. By "opinionated" we mean what the term means in software: where there is a defensible right answer, the site picks one and tells you why, instead of presenting every option as equally valid. You should still apply judgment, but you shouldn't have to start from a blank page. The site assumes you want to do this well rather than quickly. It is structured as a working reference: each section can be used as a checklist, and each page as a design or procurement conversation starter.

---

## What's inside

[**Foundations**](foundations/index.md): who this is for, principles we treat as load-bearing, and how to use the site.

[**Architecture**](architecture/index.md): the technical patterns: HIPAA-eligible deployment, RAG over patient records, grounding and hallucination mitigation, structured output, audit trails.

[**Evaluation**](evaluation/index.md): how to actually measure whether your system is safe and useful. Methodology, subgroup/bias evaluation, ongoing monitoring, red-teaming.

[**Governance**](governance/index.md): clinician-in-the-loop design, what "training the model" really means in practice, informed consent, accountability and liability.

[**Risks**](risks/index.md): domain-specific failure modes. The first deep dive is ABA treatment planning; more domains will be added.

[**Reference**](reference/index.md): the regulatory and framework backdrop (HIPAA, BACB, FDA CDS, NIST AI RMF, CHAI, WHO), plus a glossary.

[**Checklists**](checklists/index.md): the red-flags audit and deployment-readiness checklist. Use them directly in design reviews, vendor evaluations, and procurement.

---

## What this site is not

- Not a compliance product. Use it as input to your compliance work, not a replacement for it.
- Not a survey of every state AI law. The regulatory section gives you the load-bearing pieces; specialized trackers do the rest better.
- Not vendor-neutral on safety. Where there is a clear right answer (BAAs before PHI, clinician sign-off on every plan), the site says so.

## Status

Version 0.1, under active development. The site is updated by a maintainer with PRs from a weekly source-monitoring agent. See the repo for contribution details.
