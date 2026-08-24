# Benchmark results

Provider: deterministic fake; embedding: deterministic hash-384.

- Four asset pipelines: 74.9% median latency reduction (324.32 ms serial vs 81.3 ms parallel; p95 81.48 ms).
- RAG top-1 source accuracy: 100.0% baseline vs 100.0% with rewrite + RRF (0.0% relative uplift).
- Revision patch computation: p50 0.021 ms, p95 0.026 ms. This local figure excludes HTTP, SSE, database, and React build time and is not presented as end-to-end latency.
