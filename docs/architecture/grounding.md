# Grounding & hallucination mitigation

LLMs produce confident-sounding text by default. In clinical contexts, "confident-sounding" and "correct" must be decoupled, and made separately verifiable.

## Grounding rules of thumb

1. **Answer only from provided context.** System prompts should explicitly forbid drawing on parametric knowledge for patient-specific claims. If the context doesn't support an answer, the system should refuse or flag insufficient evidence.
2. **Cite or don't claim.** Every clinical claim in the output should carry an inline source citation pointing back to a document ID and (where relevant) a span.
3. **Refusal is a feature, not a failure.** A system that says "insufficient evidence in the record to recommend X" is doing its job. Reward this in evaluation; do not penalize it as a "low completion rate."

## Patterns that work

- **Citation-required prompting.** "For each recommendation, cite the supporting note ID and date. If no note supports the recommendation, omit it and add it to a 'gaps' section."
- **Refusal-on-missing-context.** Explicit refusal templates for queries where the retrieval returned nothing relevant.
- **Two-pass generation.** First pass drafts; second pass (LLM or rule-based) verifies that every claim is cited and every cited source exists.
- **Numeric and date pass-through.** Assessment scores, dates, and frequencies pass through from structured EHR fields. The model never generates these from scratch; it can quote them, format them, summarize them, but not invent them.
- **Constrained vocabularies.** Where the output must use specific terminology (DSM/ICD codes, payer-required field names, BACB-defined terms), constrain via grammar or post-validation.

## Patterns that don't work

- **"Be accurate" in the system prompt.** Models cannot self-monitor for accuracy in any meaningful way. Telling them to be accurate is theater.
- **Temperature = 0 as a hallucination fix.** Lower temperature reduces variance but does not improve groundedness. A model can be deterministically wrong.
- **Post-hoc fact-checking by the same model.** Useful as a sanity check, not as a guarantee. The model that hallucinated the claim is poorly placed to catch its own hallucination. Use a different model, or rules, or both.

## Special cases

### Numbers

Models generate numbers fluently and often wrongly. For any numeric claim that affects clinical decisions:

- The number should come from a structured source, not the model.
- The model should cite the source.
- The eval suite should include "numeric integrity" checks on a held-out set.

### Dates

Same as numbers, with one addition: relative date language ("three months ago," "since the last reauth") is a common source of off-by-one errors. Surface absolute dates in context; have the model preserve them verbatim.

### Negation and absence

"The patient does not exhibit X" and "There is no evidence in the record of X" are different claims with different clinical implications. LLMs frequently conflate them. Test for it.

## Evaluation specific to grounding

- **Unsupported-claim rate.** For a sample of N outputs, manually trace each clinical claim to a cited source. Report the fraction that are unsupported, partially supported, or supported.
- **Citation accuracy.** When the model cites a source, does the source actually support the claim? Inflated citations are worse than no citations.
- **Refusal appropriateness.** When the model refuses, was refusal the right answer? Both over- and under-refusal harm.
- **Numeric integrity.** Sample outputs containing numbers and verify each against the source.
