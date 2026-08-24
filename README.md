# Foundry — AI Website Builder

A complete, resume-grade multi-agent website generator built with Python, FastAPI, LangGraph, LangChain, PostgreSQL/pgvector, server-sent events, React, Vite, and Docker. It supports live preview, element-aware revision, source export, and one-click static publication across three code modes.

The default `fake` provider is deterministic and needs no API key. Set `MODEL_PROVIDER=openai` plus server-side `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` to use an OpenAI-compatible model for query rewriting and planning. API keys never enter the browser bundle.

## Run it

```bash
cp .env.example .env
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000) for the workspace and [http://localhost:8000/docs](http://localhost:8000/docs) for the API. PostgreSQL is internal to Compose; generated versions persist under `artifacts/`, and publications under `deployments/`.

The application image uses the PostgreSQL 16 Debian base and installs Python/Node for the service. This keeps the build reproducible in restricted Docker Hub environments while the database service still runs the pgvector PostgreSQL 16 image.

## What is implemented

- Three modes: portable single HTML, linked multi-page static, and React/Vite.
- LangGraph workflow: query rewrite → pgvector retrieval → Planner → four parallel asset pipelines → Generator → Reviewer → at most two repair rounds.
- Four asset pipelines: stock-style hero art, illustration, diagram, and branding/palette. They use deterministic SVG fallbacks, so the full path works offline.
- RAG: bundled design/accessibility guidance, 400-token chunks with 80-token overlap, three normalized queries, pgvector cosine retrieval, and reciprocal-rank fusion.
- Persistent jobs and SSE events. `Last-Event-ID` resumes after disconnect, and interrupted jobs are marked on startup.
- Immutable artifact versions with path, extension, count, per-file, and bundle-size validation. A failed validation or React build never replaces the active version.
- Sandboxed preview iframe. A preview-only bridge reports the clicked selector/text through `postMessage`; it is not written into exported code.
- Export as ZIP and one-click versioned publication to `/sites/{slug}/`.

React mode is deliberately constrained: generation may only write `src/App.tsx` and `src/styles.css`; `package.json`, Vite config, entry point, and dependencies come from the reviewed fixed template. The backend builds that template before promoting the version.

## API flow

1. `POST /api/projects`
2. `POST /api/projects/{id}/generate` → `202` job
3. `GET /api/jobs/{job_id}/events` → persistent SSE stream
4. `GET /api/projects/{id}/preview/index.html`
5. `POST /api/projects/{id}/revisions`
6. `GET /api/projects/{id}/export`
7. `POST /api/projects/{id}/deploy`

Health endpoints are `/api/health` and `/api/ready`. The readiness response reports whether the pgvector-backed knowledge collection initialized; local lexical RRF remains available as a fallback.

## Test and benchmark

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
python benchmarks/run_benchmarks.py
```

The benchmark writes machine-readable `benchmarks/results.json` and a human-readable `benchmarks/RESULTS.md`. It measures serial versus parallel asset latency, a small labeled RAG retrieval set, and 50 effective revision-patch computations. The revision microbenchmark explicitly excludes HTTP/SSE/database/build time; use the persisted `artifact.patch` event timestamps for end-to-end measurements.

Current checked-in fake-provider run: **74.9% median asset-latency reduction** (324.06 ms serial versus 81.38 ms parallel). The six-query RAG sample scored 100% top-1 accuracy for both baseline and optimized retrieval, so it provides **no defensible uplift claim yet**. The in-process revision patch measured p50 0.026 ms and p95 0.056 ms, but is not an end-to-end SSE result.

## Resume evidence policy

The original inspiration mentions 60% lower latency, 35% better RAG relevance, and sub-second revisions. This repository does not hard-code those claims. Use the checked-in benchmark output and an HTTP/SSE run from your target machine, then state only the measured results.

Evidence mapping:

- “multi-agent website-generation application” → `backend/app/workflow.py`
- “three code modes and four parallel asset pipelines” → `backend/app/generator.py`, `backend/app/assets.py`
- “query rewriting, token chunking, pgvector retrieval” → `backend/app/llm.py`, `backend/app/rag.py`
- “FastAPI and server-sent events” → `backend/app/api.py`, `backend/app/jobs.py`
- “live preview, export, one-click deployment” → `frontend/src/App.tsx`, `backend/app/artifacts.py`, `backend/app/deployment.py`

## Deliberate scope

This is a focused single-user MVP: no authentication, billing, tenant isolation, collaborative editing, or external cloud deployment. Static publication is local and deterministic. For production, move jobs to a durable queue, isolate builds in a hardened worker, add auth/quotas, object storage/CDN, malware scanning, CSP tuning, and a managed deployment provider.
