# Deployment & data plane

The single most consequential decision is where the model runs and under what contract. Get this wrong and nothing else in the architecture matters; every subsequent design decision is downstream of whether PHI can legally flow through the system at all.

## HIPAA-eligible inference

Use one of:

- **Direct enterprise contract** with the model provider, with a Business Associate Agreement (BAA) that explicitly covers the API endpoints you are using.
- **AWS Bedrock** under the AWS BAA, with the specific model confirmed in scope.
- **Google Cloud Vertex AI** under the Google Cloud BAA, with the specific model confirmed in scope.
- **Azure OpenAI** under the Microsoft BAA, with the specific deployment confirmed in scope.

Default consumer or developer-tier API access is **not** BAA-covered, even if the underlying model is the same. The contract is the difference, not the model weights.

## What to verify before sending PHI

- [ ] BAA executed with the model provider.
- [ ] BAA executed with the cloud host (if different).
- [ ] BAAs in place with every subprocessor in the chain (logging, observability, fine-tuning vendors, vector DB host).
- [ ] **Zero data retention** confirmed in writing: prompts and completions are not retained for vendor model improvement or human review.
- [ ] **Vendor-side telemetry** disabled or replaced with your own HIPAA-controlled logging.
- [ ] Specific features in scope. Not all betas, tools, or model variants are BAA-eligible. Verify the exact configuration.
- [ ] Data residency pinned to US (or your required region). HIPAA does not strictly mandate residency, but payer contracts and state law often do.
- [ ] Model improvement opt-ins disabled.

## Tenancy and isolation

Single-tenant or strongly isolated multi-tenant. If your platform serves multiple covered entities, every layer (inference, retrieval index, logs, caches) must enforce tenant boundaries. Cross-tenant retrieval is the failure mode that ends companies.

## Network architecture

- Private connectivity to inference endpoints (VPC endpoints, Private Service Connect) where supported.
- Egress controls so the model context cannot exfiltrate PHI to unintended destinations.
- Secrets in a managed secrets store, not in code or environment files.

## What "model + version" means in clinical context

Pin to a specific model version. Auto-upgrades to a "latest" alias change the system's behavior without notice: fine for a chatbot, not fine for clinical generation. Treat version changes as code changes: re-run evaluation, document the diff, get clinical sign-off.

## Common mistakes

- Treating the BAA as a procurement formality instead of a system-design constraint. Read it. Understand what's in scope.
- Forgetting that **embeddings are PHI**. The vector store hosting embeddings of clinical text needs the same controls as the EHR.
- Assuming "we'll add the BAA before launch" is acceptable. PHI sent before the BAA is in place is a breach, retroactively un-fixable.
- Leaving default vendor request-logging on. Many providers log requests by default for abuse monitoring; this requires an explicit opt-out and a contractual carve-out.
