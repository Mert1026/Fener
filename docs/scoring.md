# Cost and recommendations

The engine is deterministic for a fixed evidence snapshot and request. It never invokes an LLM.

## Cost

Each component is `requests × usage_per_request × source_rate / source_quantity`, evaluated using Decimal. Cached input is a subset of total input: uncached input = total input − cached input. Cache-read prices apply only to cached usage. Zero usage needs no price; a missing required component returns unknown cost, not zero. Native and normalized prices are retained.

Current estimates cover flat listed rates. Taxes, credit purchase fees, unlisted charges, context-dependent tiers and discounts are excluded and disclosed. An unknown request surcharge is an explicit limitation, not a guarantee of free requests. Marketplace routing quotes are excluded from recommendations by default because a specific selected endpoint may cost more. Additional reasoning usage must not also be included in output token usage.

## Constraints

Unknown required capabilities fail closed. Serving context must accommodate both the requested context and input + output workload. Explicit output limits, monthly budget, provider allowlists, open-weight requirements, availability and stale evidence are checked before ranking. Fallbacks come only from candidates satisfying the same constraints; same-model alternatives are preferred among those candidates.

## Weights and coverage

Weights are explicit, nonnegative and must sum to a positive value. Price utility is `1 − cost / maximum eligible cost` (all-free sets receive 1). Latency utility is `1 / (1 + TTFT seconds)`. These are transparent preference functions, not quality measurements. Missing metrics contribute zero weighted utility; the denominator retains all requested weights. Coverage is available requested weight / total requested weight. A zero-coverage candidate cannot be recommended.

Benchmark weights identify exact benchmark versions. Normalization requires known lower/upper bounds and direction. Unversioned or unscaled catalog scores are preserved for inspection but excluded. Current source coverage may therefore provide no normalized quality evidence. Price-only recommendations always have low task-quality confidence. No percentage confidence is invented.

The API's `task` label is descriptive; it does not silently select magical task weights. Configure requirements and weights explicitly. Internal evaluations are separate evidence and do not silently blend into public scores.

## Pareto

`pareto_ids` implements strict dominance: another candidate must be at least as good and at least as cheap, with one dimension strictly better. Identical points both remain on the frontier. Context/cost plots are labelled as context/cost, never price/quality. A quality frontier must have comparable quality evidence; missing benchmark methodology must not produce fabricated points.

## Audit and control

The public preview is read-only. Authenticated recommendation requests persist the request, response, algorithm version, evidence identifiers and timestamp. Harness policies are versioned drafts until explicitly approved. Neither ingestion nor recommendations can apply policy changes automatically.
