# Accountability & liability

Where the buck stops, and how to know.

## The credentialed clinician owns the output

In every legal, regulatory, and professional framework that applies to clinical practice, the clinician whose name is on the document is responsible for its content. AI assistance does not transfer or dilute that responsibility.

This means:

- The clinician must be able to explain and defend any plan they sign.
- "The AI generated it" is not a defense in front of a licensing board, a payer, or a court.
- Documentation should reflect the clinician's actual review and judgment, not just the AI's draft.

For ABA specifically, this individual accountability is reinforced by the BACB Ethics Code and elaborated in the **Council of Autism Service Providers (CASP) Practice Parameters for AI Use in ABA** and the **AI Consortium for ABA (AIC-ABA) Ethical Guidelines for AI in ABA** (see [ABA further reading](../risks/aba.md#further-reading)). Read alongside Jennings & Cox (2023) and Cox (2025), they form the working frame for what credentialed-clinician ownership looks like in practice when AI is in the workflow.

## Agentic systems do not transfer responsibility

When the architecture is a planning loop with tool access and persistent state (see [Agentic systems](../architecture/agents.md)), it can be tempting to treat the system itself as the actor. The system is not an actor in any morally or legally meaningful sense. It is a control loop wrapped around a probabilistic text generator. "The agent did it" is the new "the AI generated it" and lands in the same place: the credentialed clinician whose name is on the resulting record is responsible for the record, regardless of how many steps the runtime executed to produce it.

What changes with agentic architectures is *where* the clinician's responsibility attaches. With a single-turn generator, it attaches at the output. With an agentic system, accountability has to attach at named, designed checkpoints, each corresponding to an artifact the clinician reviews and signs (a draft, a proposed action, a final note). The chain of runtime steps may be long; the responsibility model should be short, specific, and inspectable. Designing those checkpoints, and resisting their erosion as workflows mature, is part of organizational accountability below.

## The organization owns the system

Organizational accountability, distinct from individual clinical accountability, covers:

- Whether the system is fit for clinical use.
- Whether evaluation and monitoring are adequate.
- Whether clinicians have the tools, training, and time to review properly.
- Whether incidents are surfaced, investigated, and responded to.

This responsibility cannot be pushed onto individual clinicians. A system that puts clinicians in an impossible position ("you're responsible, but you have 90 seconds per chart") is an organizational failure, even when an individual clinician signs off.

## Named accountable executive

A specific person (not a committee, not "IT") is responsible for:

- The system's continued fitness for purpose.
- Adverse event response.
- The relationship with malpractice and cyber insurers.
- Public statements about the system.

This person should have both clinical and operational authority. A CMO, VP of Clinical Operations, or equivalent role is typical. A pure technology executive is usually wrong unless they have deep clinical partnership.

## Malpractice and insurance

Before go-live:

- **Notify the malpractice carrier in writing** that AI-assisted documentation is in use. Some carriers have AI riders, exclusions, or rate adjustments.
- **Confirm coverage** for AI-related claims explicitly, in writing.
- **Cyber insurance** should reflect the data flows of the system, including any third-party processors.

A surprise at claim time is the worst possible time to learn coverage gaps.

## False Claims Act exposure

In US healthcare, billing for clinical work that wasn't actually performed is a federal fraud risk. Specific to AI-assisted documentation:

- Billed clinician time should reflect **actual clinician time**, not AI-generated content as if it were clinician work.
- Documentation should accurately represent what the clinician did versus what the AI drafted and the clinician reviewed.
- Misrepresentation to payers (describing AI-drafted content as fully clinician-authored) is a fraud risk, not just an ethical one.

## Vendor and subprocessor risk

Even if you build in-house, you depend on vendors (model provider, cloud host, vector DB, observability). Each adds a node where things can go wrong:

- BAA in place with each (see [Deployment](../architecture/deployment.md)).
- Vendor security posture documented.
- Incident notification timelines specified contractually. You must be told quickly enough to meet your own breach notification obligations.
- Vendor lock-in risk considered: if a vendor is acquired, sunsets a product, or fails security review, do you have a path off?

## Public statements

Marketing materials, conference talks, and patient-facing documentation are part of accountability. Claims about the system should be:

- **Specific.** Not "AI-powered care," but "our system drafts treatment plans for BCBA review."
- **Accurate.** Match what the system actually does today, not what is on the roadmap.
- **Reviewed.** A formal sign-off process for external claims, with clinical and legal review.

Overclaiming externally is both an ethical and an FTC risk. Recent enforcement actions on "AI washing" should inform copy review.

## When to pause or roll back

Pre-define the conditions under which the system is paused or rolled back:

- A category of adverse event of defined severity.
- A subgroup regression beyond a defined threshold.
- A vendor incident affecting BAA scope or data integrity.
- A regulatory change that materially affects fitness for purpose.

Rollback should be possible operationally; i.e., the system should be designed to be turned off without disabling clinical operations. If you can't function without it, you've made it indispensable too soon.
