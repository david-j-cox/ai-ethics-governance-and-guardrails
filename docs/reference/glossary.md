# Glossary

Terms used across the site. Brief definitions; deeper coverage lives in the relevant section.

**ABA (Applied Behavior Analysis)**
A field of clinical practice focused on socially significant behavior change, most often used with autistic individuals and others with developmental disabilities.

**Agent / Agentic system**
A control loop wrapped around one or more language model calls, with tool-invocation hooks and (usually) persistent state. The runtime feeds prior model output and tool returns back into subsequent model calls, so generations are conditioned on the chain so far. Distinguishing properties relative to a single-turn generator: tool use, multi-step looping, and state persistence. The system is not an actor with intentions; describing it as one obscures where the failure points are.

**Autonomy gradient**
The spectrum, defined by deployment policy, from suggestion (system produces text, clinician takes any action) to open-loop execution (runtime invokes tools without per-action human review). For clinical AI, the policy is a per-workflow choice that should default to the lowest workable level. The gradient is a property of the system you build or buy, not a property of the model.

**Aversive**
A stimulus or contingency intended to suppress behavior through unpleasant or harmful consequences. Widely repudiated in modern professional standards.

**BAA (Business Associate Agreement)**
A contract required under HIPAA between a covered entity (or business associate) and any vendor that handles PHI on its behalf.

**BACB (Behavior Analyst Certification Board)**
The credentialing body for BCBAs, BCaBAs, and RBTs. Publishes the Ethics Code for Behavior Analysts.

**BCBA (Board Certified Behavior Analyst)**
The graduate-level credential for ABA practitioners. Senior author and supervisor of treatment plans.

**CDS (Clinical Decision Support)**
Software that supports clinical decisions. Subject to a specific carve-out from FDA device regulation under 21st Century Cures §3060.

**CHAI (Coalition for Health AI)**
A multi-stakeholder coalition publishing voluntary assurance standards for health AI.

**Covered entity**
Under HIPAA, a healthcare provider, health plan, or healthcare clearinghouse that transmits PHI electronically.

**ePHI**
Electronic Protected Health Information. PHI in electronic form, subject to the HIPAA Security Rule.

**Embedding**
A vector representation of text used for similarity search in RAG. Embeddings of clinical text are PHI.

**Few-shot**
A prompting technique in which curated example inputs and outputs are inserted into the prompt to guide model behavior.

**Fine-tuning**
Adjusting a model's weights through additional training. Distinct from prompt engineering.

**Foundation model**
A large model trained on broad data, used as the base for downstream applications.

**Grounding**
Tying model outputs to specific source material, typically through retrieval and citation.

**Hallucination / confabulation**
Plausible but unsupported model output. In clinical contexts, a primary safety concern.

**HIPAA (Health Insurance Portability and Accountability Act)**
US federal law governing protection of health information. Enforced by HHS Office for Civil Rights (OCR).

**HTI-1**
ONC's Health Data, Technology, and Interoperability final rule. Includes Decision Support Intervention transparency requirements for certified EHRs.

**LLM (Large Language Model)**
A foundation model trained primarily on text, generating outputs token by token.

**MedHELM, HealthBench, MedQA**
Public benchmarks for medical AI. Useful for sanity checks; not substitutes for use-case-specific evaluation.

**Minimum necessary**
HIPAA standard requiring PHI use and disclosure to be limited to what's needed for the purpose.

**NIST AI RMF**
National Institute of Standards and Technology AI Risk Management Framework. Voluntary lifecycle scaffolding.

**OCR (Office for Civil Rights)**
HHS office enforcing HIPAA.

**ONC (Office of the National Coordinator for Health IT)**
HHS office overseeing health IT certification, including DSI transparency requirements.

**PHI (Protected Health Information)**
Individually identifiable health information held by a covered entity or business associate, regulated by HIPAA.

**Prompt engineering**
The discipline of designing prompts (system instructions, user templates, few-shot examples) to elicit desired model behavior. Distinct from training.

**RAG (Retrieval-Augmented Generation)**
A pattern in which retrieved documents are inserted into the prompt context to ground model output in specific sources.

**RBT (Registered Behavior Technician)**
The paraprofessional credential in ABA. Implements treatment plans under BCBA supervision.

**Red-teaming**
Adversarial testing of a system to find failure modes before deployment.

**RLHF (Reinforcement Learning from Human Feedback)**
A technique for adjusting model behavior using human preference data.

**SaMD (Software as a Medical Device)**
Software intended for medical purposes that performs those purposes without being part of a hardware medical device. Subject to FDA regulation.

**SFT (Supervised Fine-Tuning)**
Training on (input, output) pairs to adjust model behavior for a task.

**Shadow mode**
Running a system in production conditions without exposing outputs to end users, for evaluation purposes.

**Structured output**
Model output constrained to a defined schema (JSON, tool-use, etc.) rather than free-form text.

**Tool use**
A pattern in which a model emits text formatted as a function call, and a runtime parses that text and executes the function (search a record, send a message, schedule a session). The model does not "use" the tool; the runtime does, conditioned on the model's output. Tools turn model outputs into changes to external state and expand the system's blast radius accordingly.

**TRICARE ACD**
TRICARE Autism Care Demonstration. The DoD program for autism services, with specific structured assessment and plan requirements.

**Verifier / verifier pass**
A second pass over model output (LLM-based or rule-based) that checks invariants and flags issues before clinician review.

**Zero data retention (ZDR)**
A vendor configuration in which prompts and completions are not retained for vendor model improvement or human review. Standard for HIPAA-aligned deployments.
