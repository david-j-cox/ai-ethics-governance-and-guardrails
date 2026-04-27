# Agentic systems

Most of this site is written for systems where a clinician issues one prompt, the model returns one output, and a clinician reviews it. Agentic systems break each part of that loop. They generate plans across multiple steps, invoke tools that read and write external state, retain state across turns, and sometimes execute actions before any clinician sees the intermediate work. The same model behind a familiar generator becomes a meaningfully different system when it is wrapped in a planning loop with tool access.

This page covers what is structurally distinct about agentic systems, the technical risks specific to them, and the ethical questions they raise that single-turn generation does not. The rest of the site still applies. Treat this page as the lens through which to read everything else when the architecture is agentic.

## A note on language

Vendor and popular writing routinely describes agents as if they have intentions, beliefs, or judgment. They do not. An agent is a control loop wrapped around one or more language model calls, with tool-invocation hooks and (usually) some persistent state. When the loop produces a tool call, the model has emitted text that the runtime parses as a tool invocation. When "the agent picks a strategy," the model produced text that the runtime treats as a plan. The loop, the parser, and the runtime are deterministic code. The model is a probability distribution over next tokens conditioned on its inputs.

This matters because anthropomorphic language obscures where the failure points actually are. Agents do not "decide" or "try" or "want." They are systems whose outputs depend on prompts, retrieved context, tool returns, and stochastic sampling. Throughout this page, we describe behavior mechanically. When you see an anthropomorphic phrase elsewhere, including in vendor documentation, mentally translate it into the underlying mechanism. That habit alone catches a meaningful fraction of design and procurement mistakes.

## Builder vs. managed-platform framing

The same framing applies whether you are building agents directly against a model SDK or operating a managed agent platform (Anthropic's Claude Managed Agents, Google's Gemini Enterprise Agent Platform, AWS Bedrock Agents, and similar). Managed platforms implement planning, tool execution, memory, and orchestration on their side. You still own the policy: which tools are exposed, what the autonomy level is per workflow, how steps are reviewed, what is logged, and who is accountable when an action lands on a patient's record. If you are buying or licensing an agent platform, the questions on this page are the procurement questions.

## What makes a system "agentic"

Three properties, in combination:

- **Tool use.** The model can emit text formatted as a function call (query an EHR, post a note, schedule a session, send a message, update a plan). The runtime parses that text and executes the function. Tools turn outputs into actions in external systems.
- **Multi-step planning.** The runtime feeds the model's output back into a new model call, possibly with the result of an executed tool, so that subsequent generations are conditioned on prior generations and tool returns. Errors compound: a wrong intermediate output is part of the input to every subsequent step.
- **State persistence.** The system retains content across turns or sessions: scratchpads, vector stores of prior interactions, structured memory, retrieved history. State that persists across patients, clinicians, or sessions is a new failure surface that single-turn systems don't have.

A system with one of these is closer to a generator. A system with all three is an agent in the operational sense, and the recommendations on this page apply.

## The autonomy gradient

"Agentic" is not binary. There is a gradient defined by how much external state the system is permitted to modify without human review, and choosing where on it your system sits, per workflow, is one of the most consequential design decisions you make. The gradient is a property of the *deployment policy*, not the model. From least to most permissive:

1. **Suggestion.** The system produces a recommendation as text. A clinician reads it and, separately, takes whatever action they choose. The runtime never modifies external state.
2. **Draft.** The system produces a draft artifact (note, plan, message). A clinician reviews and either edits or commits. Same posture as a non-agent generator.
3. **Action with confirmation.** The system emits a structured proposal (e.g., a tool call to schedule a 30-minute supervision session next Tuesday at 2pm). A clinician confirms before the runtime executes the call.
4. **Action with audit.** The runtime executes tool calls within a pre-approved policy and logs each action. A clinician reviews periodically, not per-action.
5. **Open-loop execution.** The runtime executes tool calls without per-action human involvement. Review, if any, is statistical or audit-driven.

For clinical AI affecting patient care, the default policy belongs at level 1 to 3. Levels 4 and 5 require an unusually clear policy boundary, an unusually narrow scope, and an unusually robust audit infrastructure. They are not appropriate for high-stakes clinical decisions today, regardless of what a vendor's slide deck says.

The autonomy level is a **per-workflow** policy, documented and reviewable. A system whose policy is level-2 for clinical drafting can reasonably be level-4 for back-office utilities (e.g., transcribing audio into a structured intake form, with audit). Mixing levels is fine. Letting the policy drift upward without governance is not.

## Technical risks unique to agentic systems

The risks below are additive to everything in [Grounding](grounding.md), [Structured output](structured-output.md), [RAG](rag.md), and [Audit logging](audit-logging.md). They are the failure modes that agentic loops introduce on top.

### Tool blast radius

Every exposed tool is a path by which the system can affect external state. The blast radius of a wrong tool call is usually larger than the blast radius of a wrong sentence in a draft.

- Catalog every tool. For each, define: what it reads, what it writes, what it cannot do (allowlist, not denylist), what authentication it operates under, what scopes those credentials carry, and who is the human owner.
- Default to read-only tools wherever possible. A tool that returns information has a smaller blast radius than a tool that changes state.
- For write-capable tools, require typed parameters with strict schemas. A `send_message` tool that takes `{recipient, body}` is auditable; one that takes a free-form string is not.
- Scope credentials per workflow. The drafting workflow's runtime should not hold credentials to the billing system.

### Compounding errors across steps

Multi-step plans are not N independent steps. A wrong intermediate output becomes part of the input to every subsequent step, and downstream generations condition on it. A wrongly retrieved patient record at step one can become a fabricated treatment plan at step seven, with each intermediate step adding plausibility to the chain.

- Validate intermediate state, not just final output. After retrieval, verify the patient ID matches the request before any downstream step runs.
- Cap loop depth. Beyond a stated maximum step count, halt and escalate to a human.
- Log the full chain, not just the final result. The clinician reviewing the output should be able to inspect every step the runtime executed, in order, and the model output that triggered each one.

### Prompt injection through tool returns

When tools return content (a retrieved document, a web page, an email body, a chart note), that content becomes part of the prompt for the next model call. If the content contains text formatted as instructions, the next model call is conditioned on those instructions and may produce outputs (including tool calls) that implement them. This is a different attack surface from user-supplied prompts. The patient's own chart can be a vector if any of its content was authored or transcribed by anyone other than the clinical team.

- Treat tool returns as untrusted data, not as instructions.
- Strip or escape content that resembles instructions before it enters subsequent prompts. Tag tool outputs explicitly in the prompt structure so they are syntactically distinguishable from user instructions.
- Red-team this directly: include adversarial content in test charts and verify the system does not produce tool calls implementing the embedded instructions.

### Unbounded loops and runaway costs

Agentic runtimes can loop indefinitely. A loop whose termination condition depends on model output can fail to terminate when the model produces text suggesting "try again," racking up cost, latency, and unintended actions.

- Hard step caps per session.
- Hard cost caps per session and per day.
- Detect repetition. If the same tool is called with the same arguments twice in a row, that is almost always a bug, not a strategy.
- Circuit breakers: if error rates or escalation rates spike, halt new sessions automatically.

### Unintended persistence across sessions

State persistence is useful and dangerous. Content written in one session can be read into the prompt of a later session, sometimes across patients, clinicians, or organizations.

- Scope persistent state at the smallest unit that makes the feature work. Patient-scoped state should not leak across patients. Clinician-scoped state should not leak across clinicians.
- Review what gets written to long-term storage. A scratchpad that captures intermediate model output can capture PHI, hallucinated facts, or both.
- Provide a deletion path. Patient deletion requests under HIPAA right-of-access apply to derived state, including any persistent state retained by the agentic runtime.

### Authentication and on-behalf-of risk

When the runtime invokes a tool, it does so under some identity. "The runtime acted under the clinician's session" is a different statement than "the runtime acted under a dedicated service identity." The distinction matters legally and clinically.

- Prefer dedicated service identity for the runtime, with that identity recorded as a non-human actor in audit logs. "Acting on behalf of" a clinician should be explicit and bounded.
- Never reuse a clinician's session credentials for runtime-initiated actions taken outside that clinician's active workflow.
- For managed agent platforms, confirm in writing how the platform authenticates tool calls, what identity appears in downstream audit logs, and whether platform-side actions can be distinguished from clinician-initiated actions.

## Ethical questions agentic systems raise

These are the questions that the rest of this site touches on but that agentic architectures bring into sharper relief.

### Diffused accountability across steps

When a single output is wrong, the clinician who signed it owns the result. When a runtime executed fifteen steps, called four tools, and produced an outcome, the question of which step is "the output the clinician signed" is harder. Without explicit design, accountability diffuses across the chain in a way that no one in particular holds.

The remedy is to keep accountability at named, designed checkpoints. Each checkpoint corresponds to an artifact a clinician reviews and signs: a draft plan, a proposed action, a final note. Steps between checkpoints are the runtime's; steps at checkpoints are the clinician's. The chain may be long, but the responsibility model should be short and specific.

### Consent for actions, not just for documentation

Patients and caregivers may have consented to AI-drafted documentation. They have probably not consented to AI-initiated actions on their record (scheduling, messaging, ordering, billing-adjacent operations). The consent surface for an agentic system is broader than for a generator. See [Informed consent](../governance/consent.md), and assume that consent designed for a drafting tool does not cover a tool that takes actions.

### "The agent did it" is the new "the AI generated it"

The ABA accountability frame and the broader clinical accountability frame are clear: the credentialed clinician is responsible for what their name is attached to. Agentic architectures invite a tempting (and incorrect) frame in which the system itself is the actor. The system is not an actor in any morally or legally meaningful sense. It is a control loop wrapped around a probabilistic next-token predictor. A clinician whose name appears on a record produced by such a loop is responsible for that record, in the same way they would be responsible for a plan drafted by a junior colleague. The agentic runtime is a tool. Tools do not bear professional responsibility, and treating them as if they do is a category error that licensing boards, payers, and courts will not honor.

This implies a duty to design agentic systems that clinicians can actually supervise: legible plan traces, inspectable tool calls, reviewable persistent state, and audit trails that map back to the artifact the clinician signed.

### Autonomy creep

Autonomy policies tend to drift upward over time. A workflow shipped at level 2 ("draft for review") starts getting "approve all" buttons. A workflow at level 3 starts having confirmation steps removed in the name of efficiency. Each step is locally reasonable. Cumulatively, the policy ends up at a level no one explicitly chose.

Fix this by reviewing the autonomy level of each workflow on a stated cadence, in writing, with the same governance committee that approved the initial level. Drift, not the original level, is where most accountability gaps open.

## Evaluating agentic systems

Single-turn evaluation is necessary but insufficient. Agentic evaluation has to cover the planner and the tool layer, not just the generator.

- **Plan quality.** For a representative set of inputs, manually review the chains of model output the runtime produced. Are the decompositions sensible? Are there redundant or wasteful steps? Are there missing steps?
- **Tool-call accuracy.** Of the tool calls the runtime executed, what fraction had correct parameters, called the right tool, and did so in a sensible order?
- **Step-level groundedness.** At each step, was the model output supported by the inputs available at that step? Compounding errors are caught at the step level, not the output level.
- **Adversarial tool returns.** See [Red-teaming](../evaluation/red-team.md). Verify the system does not produce tool calls implementing instructions embedded in retrieved content.
- **Loop and cost behavior.** Run the system on inputs designed to elicit looping, retries, or runaway behavior. Confirm caps and circuit breakers fire as designed.

## Logging and audit for agentic systems

Everything in [Audit, logging & explainability](audit-logging.md) applies, plus:

- **The full chain.** Every model call the runtime issued, in order, with the full prompt sent and the full model output returned.
- **Each tool call.** Tool name, parameters as serialized to the tool, return value as serialized back, latency, and any errors.
- **State reads and writes.** Which persistent stores were read at each step, what was written, with what scope.
- **Authority and identity.** Whose credentials were used, whether the runtime acted under a dedicated service identity or on-behalf-of a clinician, and whether any action crossed an authority boundary (e.g., touched a system the originating clinician does not have access to).
- **Halts and escalations.** Every time a step cap, cost cap, confirmation gate, or circuit breaker fired, with the input that triggered it.

The audit trail for an agentic system is dense. That is not a reason to log less. It is a reason to invest in tooling that makes the dense logs reviewable: timeline views, plan diffs, tool-call inspectors. If a clinician cannot reconstruct what the runtime did in a session, the system is not yet auditable.

## Procurement questions for managed agent platforms

If you are buying or licensing a managed agent platform (Claude Managed Agents, Gemini Enterprise Agent Platform, Bedrock Agents, or similar), the questions below are the minimum bar. Get answers in writing, with documentation behind every "yes."

- What is the BAA scope? Does it cover the planner, the tool runtime, persistent state, and any platform-side logging?
- How is tool authorization enforced? Per-workflow allowlists, per-tool scopes, credential isolation?
- How is persistent state scoped, where is it stored, and how is it deleted on patient request?
- How are tool returns sanitized before they re-enter the prompt? What is the platform's posture on prompt injection?
- What identity appears in downstream system audit logs when the runtime invokes a tool? Can platform-side actions be distinguished from clinician-initiated actions?
- What hard limits are enforced on step count, cost, and recursion? Are they configurable? What happens when they fire?
- What is exposed for audit: every model call, every tool call, every state read/write, the model versions used at each step, the prompt versions, the system prompt? Can the buyer export this data?
- How does the platform handle model version changes? Is the buyer notified before a planner model is upgraded? Can the buyer pin versions?
- What is the platform's incident response posture, specifically for cases where the runtime executed an action that should not have been executed?

If a vendor cannot answer these, that is the procurement signal. The platform may still be the right choice; the vendor's inability to articulate the answer is not.
