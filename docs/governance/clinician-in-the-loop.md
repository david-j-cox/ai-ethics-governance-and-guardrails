# Clinician-in-the-loop

"Human in the loop" is the most over-used phrase in clinical AI. It can mean anything from "a clinician glances at outputs in batches" to "every output is independently re-derived." The phrase is meaningful only with detail.

## What good review looks like

The clinician should be able to:

1. **See the inputs the system saw.** Source notes, retrieved context, structured fields.
2. **See the system's output and its citations.** Each clinical claim mapped to a source.
3. **Edit any field freely.** The system should never make edits hard or punitive.
4. **Surface or override verifier flags.** With a recorded reason where applicable.
5. **Sign off explicitly.** Sign-off is an action, not a default state.

## What rubber-stamping looks like

- Edit rate trending toward zero.
- Time-to-sign trending toward seconds.
- Sign-off as the path of least resistance.
- No mechanism for the clinician to flag uncertainty.

Rubber-stamping is the most likely way a well-built system harms patients. The system itself must be designed to discourage it.

## Designing against rubber-stamping

- **Friction in the right places.** Sign-off should require an active step, not auto-progress.
- **Highlight changed fields and citations.** Force visual attention to where the model is most likely to have erred.
- **Show uncertainty.** Where the system is uncertain (low retrieval recall, refused fields, verifier flags), surface it visibly.
- **Track and surface edit rates.** A clinician whose edit rate has trended to zero gets a dashboard nudge.
- **Spot-check audits.** A random sample of signed plans is reviewed by a peer; results are shared back as learning.

## Review workflow design choices

### Synchronous vs. asynchronous

- **Synchronous** (clinician interactively reviews the draft as it's produced): better for high-stakes generation, slower at scale.
- **Asynchronous** (system drafts in batch; clinician reviews in a queue): scales better, risks queue-pressure shortcuts.

Most clinical settings end up hybrid: synchronous for initial assessments and high-risk cases, asynchronous for routine reauthorization or summaries.

### Tiered review

Not every case needs the same depth of review. Tier by risk:

- **Tier 1:** complex / high-stakes (initial assessments, severe behavior, medical complexity), substantive synchronous review.
- **Tier 2:** routine reauth, well-known cases, asynchronous review with attention to changes.
- **Tier 3:** non-clinical formatting and administrative content, light review.

Tiering must be transparent: the clinician knows what tier this case is in and why.

### Escalation paths

The system must always offer a path to escalate:

- "I don't agree with this draft" → human-only re-derivation, with reasons captured.
- "I'm not the right reviewer for this" → reassignment.
- "Something is wrong" → adverse event log entry.

## Supervision of trainees and paraprofessionals

For ABA and similar fields where supervised credentials (RBTs, BCaBAs) implement plans authored by a senior clinician (BCBA), the system must not blur supervision lines:

- Authoring credential is unchanged: the senior clinician owns the plan.
- Trainees and paraprofessionals see the plan, not the AI draft pre-review.
- Supervision documentation (per BACB or analogous standards) reflects the senior clinician's actual review activity.

## The clinician is not a guardrail

A common framing, "the clinician is the safety check," is true and dangerous. True, because they catch errors the system will make. Dangerous, because it can be used to justify shipping a less-safe system. The clinician's review reduces residual risk; it does not licence raising the baseline risk by relying on them. Build the safest system first; then layer review.
