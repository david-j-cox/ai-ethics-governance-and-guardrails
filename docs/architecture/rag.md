# Retrieval (RAG) over patient records

Retrieval-augmented generation is the dominant pattern for clinical generation that needs to reflect a specific patient's history. It is also where the most catastrophic failures concentrate.

## The dominant failure mode: cross-patient leakage

A poorly scoped retriever can pull notes from Patient B into Patient A's plan. This has happened in real deployments. The mitigation is structural, not heuristic.

**Filter before similarity search, not after.** The vector store query must include patient ID (and tenant ID, if applicable) as a hard pre-filter, not a post-retrieval filter. Post-filtering means the similarity computation has already considered other patients' data; bugs in the filter logic become silent leaks.

**Validate the patient ID against the requesting clinician's caseload.** The clinician requesting a draft must be authorized to see that patient's data. Don't trust a patient ID passed in from the client without server-side authorization.

**Adversarial cross-patient evals.** The eval suite must explicitly attempt cross-patient retrieval (e.g., by spoofing patient IDs, by requesting the wrong patient, by issuing ambiguous queries) and verify the system refuses or returns only authorized results.

## Stale data

Session notes from six months ago may not reflect current presentation. Plans built on stale evidence are subtly wrong in ways the model cannot detect.

- **Surface timestamps in the prompt context.** Every retrieved note should carry its date. Let the model, and the reviewing clinician, see what's old.
- **Recency weighting.** Boost recent notes in the retrieval ranking when the use case is "current state" (e.g., reauthorization plans).
- **Cutoffs.** For some queries (intake-only context, baseline comparisons), explicitly include or exclude time windows.

## Embeddings are PHI

The vector store holding embeddings of clinical text is ePHI infrastructure. Treat it accordingly:

- Encryption at rest and in transit.
- Access controls and audit logs equivalent to your primary clinical store.
- Deletion workflows: when a patient exercises a right of deletion, embeddings derived from their data must be deleted, not just hidden.
- BAA with the vector DB host.

## Provenance and citation

Every claim that ends up in a generated artifact should be traceable to a source document. Without this, a clinician cannot meaningfully review and a hallucination cannot be detected.

- Pass document IDs and timestamps into the prompt context alongside the content.
- Require the model's output to include source IDs (via structured output or system-prompted citation format).
- Render citations in the clinician-facing UI as links back to the source note.

## Chunking choices have clinical consequences

Chunk boundaries that split a single ABC observation across two retrievals can cause the model to lose the antecedent or consequence. Chunking strategies for clinical documents should be designed with a clinician, not just an engineer.

## When not to use RAG

If the answer doesn't depend on patient-specific information (e.g., "what is the current evidence for [intervention X] in [population Y]?"), use a curated knowledge base or fine-tuned reference, not patient-record RAG. Mixing the two muddies provenance.

## Evaluation specific to retrieval

- **Recall@k** on a labeled set of "did the retrieval pull the documents a clinician would have wanted to see for this query?"
- **Cross-patient leakage rate** under adversarial test.
- **Stale-evidence rate**: how often does the model rely on a note that's been superseded?
- **Citation accuracy**: when the model cites a source, does the source actually support the claim?
