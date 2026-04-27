# What "training the model" actually means

When leadership says "we'll have our clinicians train the model," that phrase covers a wide range of approaches with very different cost, complexity, and effect. Being precise is worth real money and real safety.

## The spectrum, from most to least feasible in-house

| Approach | What it is | Affects model weights? | Realistic in-house? |
|---|---|---|---|
| **Prompt engineering & version control** | Iterating system prompts, instructions, and few-shot examples | No | Yes, start here |
| **Few-shot example curation** | Curated exemplar inputs/outputs inserted into prompts | No | Yes |
| **RAG corpus curation** | Clinicians select and version-control which protocols, papers, goal banks feed retrieval | No | Yes, high leverage |
| **Output preference collection** | Clinicians rate, rank, or correct outputs; data feeds future iteration | No (initially) | Yes |
| **DPO / RLHF on collected preferences** | Adjusts model weights based on rater preferences | Yes | Possible but expensive; limited turnkey availability for frontier models |
| **Supervised fine-tuning (SFT)** | Train on (input, ideal-output) pairs | Yes | Available for some models; significant data-curation cost |
| **Full foundation-model fine-tune** | Continued pretraining on domain data | Yes | Not realistic for most clinical orgs |

## Where the value actually comes from

For most teams, the top three rows account for ~80% of the practical value:

1. **Prompt engineering and version control.** Most clinical-quality issues are prompt issues. A well-iterated prompt outperforms a poorly fine-tuned model on most tasks.
2. **Few-shot examples.** A handful of well-chosen exemplars can shape output more than weeks of fine-tuning data collection.
3. **RAG corpus curation.** What the system retrieves shapes what it says. Clinical leadership owning the corpus is high-leverage and underrated.

## When fine-tuning is actually warranted

Consider it when:

- You have a specific failure mode that prompt engineering and RAG can't fix (rare, in clinical generation).
- You have access to high-quality (input, output) pairs at scale, with clinical sign-off.
- You can afford the eval cost of a tuned model. Eval becomes harder, not easier, after fine-tuning, because you've changed the base distribution.
- You can manage the lifecycle: tuned models are tied to a base version and need re-tuning when the base changes.

If you're unsure, you don't need it yet.

## Collecting preference data without fine-tuning

You can, and should, start collecting structured clinician feedback even if you have no near-term plans to fine-tune. Reasons:

- It informs prompt and corpus iteration.
- It surfaces patterns of edit and disagreement.
- It builds the dataset that *might* be used for future tuning.
- It demonstrates clinician engagement, which matters for governance and adoption.

What to capture:

- The original draft and the clinician's edited version (diff).
- Optional reason codes (factually wrong, missing element, wrong tone, prohibited language, etc.).
- Free-text rationale for nontrivial edits.
- Sign-off identity and timestamp.

## Be honest with leadership

If a leader says "our clinicians are training the model," ask: which row in the table above? If the honest answer is "row 1" (prompt engineering), say so. The capability is real and valuable; the framing matters because it sets expectations for cost, timeline, and what kind of company you're building.

## Be honest with payers and patients

When describing the system in payer materials, marketing, or patient-facing language, use language that matches what's actually happening. "Clinician-curated AI" is honest. "Trained by clinicians" usually isn't, unless you've done supervised fine-tuning or RLHF.
