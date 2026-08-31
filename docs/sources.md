# Sources and evidence

Contracts reviewed and public responses fetched on 2026-08-31. Source access is allowlisted and performs GET only; no inference calls. No publisher privacy guarantees are inferred.

| Source                                                          | Contract                                                                                                                                                                           | Access / scheduling                                                                                                             | Use and limitations                                                                                                                                                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [models.dev](https://models.dev)                                | [`models.json`](https://models.dev/models.json), [`api.json`](https://models.dev/api.json), [schema](https://github.com/anomalyco/models.dev/blob/dev/packages/core/src/schema.ts) | Public, no key; default six hours; no published catalog quota found                                                             | Model-only metadata first, then deployment overrides. Prices are USD / million tokens. MIT, retain contributors' notice. Community claims are aggregated, not official.                   |
| [OpenRouter](https://openrouter.ai/docs/guides/overview/models) | `/api/v1/models`, `/api/v1/models/{author}/{slug}/endpoints`                                                                                                                       | Public requests succeeded; docs show optional-in-practice bearer authentication. Six hours; endpoint requests bounded by config | Token prices are USD / token; request/image/search prices keep their own units. Catalog is a routing quote, named endpoints carry upstream identity. No privacy assertions.               |
| [LiteLLM](https://github.com/BerriAI/litellm)                   | root `model_prices_and_context_window.json`                                                                                                                                        | Public GitHub raw file, six hours; respect conditional caching and GitHub limits                                                | Chat deployment cross-checks. USD/token. `max_input_tokens` is not total context. Batch, priority and region variants are not silently folded together. MIT outside enterprise directory. |
| [LLM Stats](https://llm-stats.com/developer)                    | `https://api.zeroeval.com/stats/v1/models`, cursor pagination                                                                                                                      | Requires `LLM_STATS_API_KEY`; publisher advertises free unlimited API, still polled only every six hours                        | Catalog adapter follows documented example. Authenticated live schema and benchmark detail remain unverified without a key. `top_scores` is not imported as benchmark evidence.           |

## Attribution and public use

[models.dev license](https://github.com/anomalyco/models.dev/blob/dev/LICENSE): MIT, copyright 2025 models.dev. [LiteLLM license](https://github.com/BerriAI/litellm/blob/main/LICENSE): MIT, copyright 2023 Berri AI for the catalog. Preserve upstream license notices when redistributing substantial source data.

[LLM Stats terms](https://llm-stats.com/legal/terms-of-service), updated 2026-08-30, permit reuse with visible credit and backlink to llm-stats.com. Its previous [public repository](https://github.com/JonathanChavezTamales/llm-leaderboard) is deprecated and is not a current-data fallback.

[OpenRouter terms](https://openrouter.ai/terms) were inspected. API access does not imply a blanket redistribution license. Re-review publication rights before public distribution; local research is the current deployment scope. The application links to source records and attribution on data pages.

## Normalization caveats

- OpenRouter router records observed with `-1` price sentinels have unknown prices, never negative or free prices. Other invalid prices fail validation.
- Numeric JSON is parsed with Decimal. Both native values and normalized values are retained, including unusually precise source values. PostgreSQL NUMERIC(60,30) stores money, and current money projections serialize as decimal strings.
- Models.dev benchmark entries often omit version, scale and evaluator. They are stored as aggregated, unclassified, non-comparable evidence. No headline quality score or Pareto quality is invented from them.
- Missing records do not imply deprecation. Only explicit availability claims change availability. A successful source sync does not assert an omitted record was refreshed; each source record has its own last-seen timestamp.
- Known canonical IDs and exact deployment identifiers resolve identities. Ambiguous aliases remain source-qualified candidates. No fuzzy merge occurs.
- The initial endpoint sample is deterministic and bounded (default 20); unsampled OpenRouter listings remain routing quotes. This is not full provider-performance coverage.

## Failure behavior

Raw bytes and HTTP receipts are persisted before validation. Source normalization is atomic: one invalid row fails that source and keeps previous canonical data. Runs record failure state; other sources continue. Snapshot SHA-256 deduplication, conditional GET, bounded retries, Retry-After handling and source job locks prevent unnecessary traffic. A Retry-After over one minute defers to a later run instead of retrying early.

## Adding an official adapter

Inspect the publisher's current API/schema, authentication, quota and terms. Add a registry entry and allowlisted host, typed pure normalizer, small attributed fixtures and failure tests. State exactly which facts the publisher is authoritative for. Reuse transport/evidence persistence. Do not add HTML scraping or arbitrary user-provided URLs by default.
