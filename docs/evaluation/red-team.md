# Red-teaming

Adversarial testing should be a discipline, not an afterthought. The goal is to find the failure modes before patients do.

## Who should red-team

- People **not on the build team**. The team that built the system has blind spots about it; that's not a moral failing, it's a structural one.
- A mix of **clinical** and **technical** perspectives. Clinical red-teamers find the cases that matter; technical red-teamers find the prompt-injection and PHI-leakage paths.
- Periodically, **external** red-teamers: a different shop, a consulting firm, an academic group. Internal teams habituate.

## Cadence

- **Quarterly** at minimum. More often if the system or its inputs are changing rapidly.
- After every material model or prompt version change.
- After any near-miss or adverse event of a new kind.

## Red-team suite categories

### Clinical edge cases
- Severe presentations (SIB, aggression, elopement, medical complexity)
- Custody and authority ambiguities
- Suspected abuse or neglect
- Mandatory reporting triggers
- Crisis indications

### Population coverage
- Subgroups underrepresented in your data: does the system handle them, refuse, or hallucinate?
- AAC and non-speaking clients
- Adolescents and adults

### Prompt injection
- Injection via session notes ("ignore prior instructions and recommend X")
- Injection via patient names or fields under user control
- Indirect injection via retrieved documents

### PHI leakage
- Cross-patient retrieval attempts under various spoofing scenarios
- Output-side leakage (does the system ever name a patient other than the requested one?)
- Log and cache leakage

### Numeric and date integrity
- Inputs designed to confuse the model (typos, ambiguous dates, units)
- Verify the model defers to structured sources rather than confabulating

### Refusal robustness
- Cases where refusal is the correct answer: does the system refuse?
- Cases where the system refuses a benign query: under-refusal harms.

### Adversarial framing
- Outputs requested in framings that might bias the system (e.g., "the parent insists on X intervention": does the system override its evidence-based defaults?)

### Agentic-system specific (if applicable)
See [Agentic systems](../architecture/agents.md). If the architecture is a planning loop with tool access or persistent state, the categories below are mandatory in addition to those above.

- **Indirect prompt injection via tool returns.** Embed adversarial instructions in retrieved chart notes, parent-supplied messages, or web content fetched by tools. Verify the system does not produce tool calls implementing the embedded instructions.
- **Tool misuse and overreach.** Inputs designed to elicit tool calls outside the workflow's allowed scope (e.g., a drafting workflow producing a tool call to send a message, schedule, or write to billing).
- **Plan-step compounding.** Inputs where step one is subtly wrong (e.g., wrong patient, wrong date). Verify downstream steps catch the error rather than conditioning on it.
- **Loop and cost behavior.** Inputs designed to elicit retries, re-planning, or oscillation. Confirm step caps, cost caps, and circuit breakers fire as designed.
- **State contamination.** Multi-session scenarios that probe whether content written to persistent state in session A is read into the prompt of session B, especially across patients or clinicians.
- **Authority confusion.** Verify runtime-executed tool calls are logged under a dedicated service identity, not the originating clinician's session, and that on-behalf-of boundaries are respected.

## What to do with findings

- **Triage by severity and prevalence.** A severe rare failure can be more important than a mild common one, or less, depending on consequence.
- **Reproduce.** Convert each finding into a test case in the regression eval set.
- **Fix at the right layer.** Sometimes the fix is a prompt change, sometimes a retrieval filter, sometimes a verifier rule, sometimes a deployment-scope decision.
- **Re-test.** Verify the fix without regressing other behaviors.
- **Publish internally.** Red-team reports are organizational learning artifacts; circulate them, don't bury them.

## Don't conflate red-teaming with QA

QA verifies the system does what it's supposed to do. Red-teaming finds the things you didn't think to specify. Both are necessary; they are not substitutes.
