# Sources and evidence

Active catalog sources are public, read-only feeds and require no API key. Source access is allowlisted and performs GET only; no inference calls occur during ingestion.

| Source                                        | Contract                                                                                                                                                                           | Access / scheduling                                             | Use and limitations                                                                                                                                                                      |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [models.dev](https://models.dev)              | [`models.json`](https://models.dev/models.json), [`api.json`](https://models.dev/api.json), [schema](https://github.com/anomalyco/models.dev/blob/dev/packages/core/src/schema.ts) | Public, no key; default six hours                               | Model metadata and deployment observations. Prices are USD / million tokens. MIT, retain contributors' notice. Community claims are aggregated, not official.                            |
| [LiteLLM](https://github.com/BerriAI/litellm) | `model_prices_and_context_window.json`                                                                                                                                             | Public GitHub raw file; default six hours; conditional requests | Deployment cross-checks. USD/token. `max_input_tokens` is not total context. Batch, priority and region variants are not silently folded together. MIT outside its enterprise directory. |

[models.dev's license](https://github.com/anomalyco/models.dev/blob/dev/LICENSE) is MIT, copyright 2025 models.dev. [LiteLLM's license](https://github.com/BerriAI/litellm/blob/main/LICENSE) is MIT, copyright 2023 Berri AI for the catalog. Preserve upstream notices when redistributing substantial source data.

## Retired integrations

OpenRouter and LLM Stats were removed from the registry, network allowlist, CLI and worker schedule. Fener cannot fetch or queue them and has no configuration fields for their keys. Existing database records, raw snapshots and citations remain for provenance; `ensure_sources` disables those old source rows and marks them `retired`. Public feeds may still describe deployments from many providers, but Fener does not contact those providers.

## Normalization caveats

- Numeric JSON is parsed with Decimal. Both native and normalized values are retained, including unusually precise source values. PostgreSQL NUMERIC(60,30) stores money, and current money projections serialize as decimal strings.
- models.dev benchmark fields are retained only inside raw historical snapshots and are not normalized into benchmark tables. The benchmark API accepts only cited Z.ai research extractions.
- Missing records do not imply deprecation. Only explicit availability claims change availability. Each source record has its own last-seen timestamp.
- Known canonical IDs and exact deployment identifiers resolve identities. Ambiguous aliases remain source-qualified candidates. No fuzzy merge occurs.
- A direct LiteLLM entry in OpenAI's own provider namespace uses the exact API model ID as `openai/<api-model-id>`. This resolves the identity while its prices and capabilities remain labeled as aggregated LiteLLM evidence.

## Failure behavior

Raw bytes and HTTP receipts are persisted before validation. Source normalization is atomic: one invalid row fails that source and keeps previous canonical data. Runs record failure state; the other active source continues. Snapshot SHA-256 deduplication, conditional GET, bounded retries, Retry-After handling and source job locks prevent unnecessary traffic.

## Z.ai research

Manual research is separate from catalog ingestion. It uses only `ZAI_API_KEY`: one documented [web-search request](https://docs.z.ai/api-reference/tools/web-search), local filtering to approved domains, then one [chat-completion request](https://docs.z.ai/api-reference/llm/chat-completion) for a cited summary. The Z.ai general API is separate from its Coding Plan endpoint ([authentication and endpoint guidance](https://docs.z.ai/api-reference/introduction)). Manual notes remain private. Benchmark updates use a separate explicitly triggered durable queue across all resolved models; only complete cited benchmark claims are exposed, and no other catalog facts are changed.
