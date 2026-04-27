# Architecture

The technical patterns that distinguish a defensible clinical-LLM system from a slick demo.

- [**Deployment & data plane**](deployment.md): HIPAA-eligible hosting, BAAs, residency, telemetry hygiene.
- [**Retrieval (RAG) over patient records**](rag.md): patterns and the failure modes that matter.
- [**Grounding & hallucination mitigation**](grounding.md): making correctness checkable.
- [**Structured output & verification**](structured-output.md): schemas, tool-use, second-pass verifiers.
- [**Audit, logging & explainability**](audit-logging.md): what to record, for how long, and why.
- [**Agentic systems**](agents.md): the technical and ethical questions that show up when the architecture is a planning loop with tool access and persistent state. Read this if any part of your stack is or is becoming agentic, including managed platforms like Claude Managed Agents or Gemini Enterprise Agent Platform.

A note on scope: this section describes patterns, not products. Specific vendors are mentioned where the choice of vendor materially changes what you can do safely (e.g., HIPAA-eligible inference endpoints).
