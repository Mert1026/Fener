# Data model

Organizations identify publishers; providers identify access/inference services. Models hold intrinsic identity, family, release and open-weight claims; deployments hold serving limits, capabilities and availability. Aliases are unique within source/entity scope. Unknown publishers stay unknown.

Source → ingestion run → snapshot → source record → observation is the evidence chain. Native JSON survives normalization. SHA-256 deduplicates raw bytes; fingerprints deduplicate identical records. Retrieval/last-seen is distinct from observation/effective time. Repeated fetches refresh liveness without fabricating price changes.

Query-critical fields are relational. Field observations preserve provenance; prices use NUMERIC(30,12), currency, quantity, unit and metric. Projections point to selected observations. Conflicts link observations and events retain before/after evidence. Ingestion never deletes history.

Benchmarks include version, category, owner, scale and direction. Results retain raw score, evaluator and verification. Unknown scales cannot be normalized. Internal evaluations are separate from public benchmarks.

Harness roles and versioned policies define requirements and weights. Telemetry excludes prompts. Evaluation runs retain scorer versions. Recommendation runs preserve inputs and outputs. Automatic policy application stays off.
