import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.assets import (
    branding_pipeline,
    diagram_pipeline,
    illustration_pipeline,
    stock_pipeline,
)
from backend.app.generator import generate_bundle, revise_bundle
from backend.app.llm import ModelGateway
from backend.app.models import CodeMode
from backend.app.rag import KnowledgeBase
from backend.app.schemas import SitePlan

PIPELINES = (stock_pipeline, illustration_pipeline, diagram_pipeline, branding_pipeline)


async def latency_sample(parallel: bool) -> float:
    started = time.perf_counter()
    if parallel:
        await asyncio.gather(*(pipeline("benchmark studio") for pipeline in PIPELINES))
    else:
        for pipeline in PIPELINES:
            await pipeline("benchmark studio")
    return (time.perf_counter() - started) * 1000


def percentile(values, ratio):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * ratio))]


async def main():
    serial = [await latency_sample(False) for _ in range(12)]
    parallel = [await latency_sample(True) for _ in range(12)]
    reduction = (1 - statistics.median(parallel) / statistics.median(serial)) * 100
    gold = json.loads((ROOT / "benchmarks/gold_queries.json").read_text())
    kb = KnowledgeBase()
    gateway = ModelGateway()
    baseline_hits = optimized_hits = 0
    for item in gold:
        baseline = kb.retrieve([item["query"]], 1)
        rewritten = await gateway.rewrite(item["query"])
        optimized = kb.retrieve(rewritten, 1)
        source_text = next(
            path.read_text()
            for path in (ROOT / "backend/knowledge").glob("*.md")
            if path.name == item["source"]
        )
        baseline_hits += int(bool(baseline and baseline[0] in source_text))
        optimized_hits += int(bool(optimized and optimized[0] in source_text))
    generated_assets = await asyncio.gather(
        *(pipeline("revision benchmark") for pipeline in PIPELINES)
    )
    plan = SitePlan(
        title="Benchmark Studio",
        audience="teams",
        pages=["index"],
        sections=["hero"],
        tone="clear",
        palette=["#6d5dfc", "#20c997", "#0d1526", "#f7f7fb"],
    )
    bundle = generate_bundle(
        CodeMode.single_html, "A benchmark studio website", plan, generated_assets
    )
    revisions = []
    for index in range(50):
        started = time.perf_counter()
        revise_bundle(
            bundle,
            CodeMode.single_html,
            f"Make revision {index} clearer",
            {"selector": "section.hero"},
        )
        revisions.append((time.perf_counter() - started) * 1000)
    baseline_rate = baseline_hits / len(gold)
    optimized_rate = optimized_hits / len(gold)
    results = {
        "environment": {
            "provider": "fake",
            "embedding": "deterministic-hash-384",
            "samples": {"assets": 12, "rag": len(gold), "revisions": 50},
        },
        "parallel_assets": {
            "serial_median_ms": round(statistics.median(serial), 2),
            "parallel_median_ms": round(statistics.median(parallel), 2),
            "parallel_p95_ms": round(percentile(parallel, 0.95), 2),
            "latency_reduction_percent": round(reduction, 1),
        },
        "rag": {
            "metric": "top-1 source accuracy",
            "baseline": round(baseline_rate, 3),
            "optimized_rewrite_rrf": round(optimized_rate, 3),
            "relative_uplift_percent": round(
                ((optimized_rate - baseline_rate) / baseline_rate * 100) if baseline_rate else 0, 1
            ),
        },
        "revision_patch": {
            "scope": "in-process effective patch; excludes HTTP/SSE/database",
            "p50_ms": round(statistics.median(revisions), 3),
            "p95_ms": round(percentile(revisions, 0.95), 3),
        },
    }
    (ROOT / "benchmarks/results.json").write_text(json.dumps(results, indent=2) + "\n")
    markdown = f"""# Benchmark results\n\nProvider: deterministic fake; embedding: deterministic hash-384.\n\n- Four asset pipelines: {results["parallel_assets"]["latency_reduction_percent"]}% median latency reduction ({results["parallel_assets"]["serial_median_ms"]} ms serial vs {results["parallel_assets"]["parallel_median_ms"]} ms parallel; p95 {results["parallel_assets"]["parallel_p95_ms"]} ms).\n- RAG top-1 source accuracy: {baseline_rate:.1%} baseline vs {optimized_rate:.1%} with rewrite + RRF ({results["rag"]["relative_uplift_percent"]}% relative uplift).\n- Revision patch computation: p50 {results["revision_patch"]["p50_ms"]} ms, p95 {results["revision_patch"]["p95_ms"]} ms. This local figure excludes HTTP, SSE, database, and React build time and is not presented as end-to-end latency.\n"""
    (ROOT / "benchmarks/RESULTS.md").write_text(markdown)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
