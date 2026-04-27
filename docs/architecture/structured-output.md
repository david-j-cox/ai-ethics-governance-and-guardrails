# Structured output & verification

Free-form clinical narrative is hard to evaluate, hard to validate, and easy to drift. Structured output (JSON schemas, tool-use, typed fields) turns the generation problem into a constraint-satisfaction problem.

## Why structured output matters clinically

- **Completeness is checkable.** A schema with required fields makes "is this plan complete?" a deterministic check, not a judgment call.
- **Payer/regulatory alignment.** Plan elements required by Medicaid, TRICARE, or commercial payers map cleanly to schema fields. Missing fields fail validation, not audits.
- **Verification is mechanical.** A second pass can check field-level invariants ("every behavioral target has a baseline AND a mastery criterion AND a generalization plan") without re-reading prose.
- **Interoperability.** Structured output flows into EHRs, dashboards, and analytics with no lossy parsing step.

## What to structure

- **Plan-level metadata:** patient ID, clinician ID, plan type (initial / reauth), period, version.
- **Targets and goals:** target name, operational definition, baseline, mastery criteria, generalization criteria, mastery date (if applicable), source citations.
- **Interventions:** intervention type, evidence base citation, contraindications considered, least-restrictive justification.
- **Outcome measures:** instrument, score, date, source.
- **Narrative sections** that can stay free-text but should be bounded (e.g., "summary of progress, ≤ 250 words, must reference at least 3 cited sources").

## The verifier pass

A second pass (LLM, rule-based, or both) checks invariants the first pass cannot reliably enforce. Examples:

- Every behavioral target has a baseline.
- Every goal has a mastery criterion.
- Every "client demonstrated X" claim has a supporting source ID.
- No prohibited intervention vocabulary appears (aversives, restraint without justification, "indistinguishability" framing).
- Dates are internally consistent (mastery date is after baseline date).
- Numeric values are within plausible ranges for the assessment instrument.

The verifier returns a structured report. The system either auto-fixes (for trivial issues) or surfaces the issues to the clinician for resolution.

## What not to over-structure

- Narrative clinical reasoning, when the structure would force the model to omit nuance the clinician needs to see.
- Anything where the right answer is "it depends." Over-structuring forces false precision.
- Sections where a typed schema would be brittle to legitimate clinical variation.

The right level of structure is the one that makes the most invariants checkable without flattening the clinical judgment the system is meant to support.

## Schema versioning

Schemas evolve. Treat schema changes like database migrations:

- Versioned, with explicit release notes.
- Backward-compatible where possible; breaking changes require clinical sign-off.
- Generated outputs carry the schema version they were produced under.
