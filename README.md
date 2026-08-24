# Foundry — AI Website Builder

Foundry turns natural-language requirements into working websites. It coordinates planning, design retrieval, asset creation, code generation, validation, preview, revision, export, and local publishing in one workflow.

## Core capabilities

- Generates portable single-page HTML, multi-page static sites, and React/Vite projects
- Orchestrates planning, four parallel asset pipelines, code generation, review, and automated repair with LangGraph
- Retrieves design and accessibility guidance through a pgvector-backed RAG pipeline
- Streams persistent job progress through resumable server-sent events (SSE)
- Supports sandboxed live preview and element-aware revisions
- Validates and versions generated artifacts before promoting them
- Exports source code as ZIP and publishes versioned static sites locally
- Provides a deterministic offline provider for development and testing

## Workflow

```text
User prompt
   ↓
Query rewrite + RAG retrieval
   ↓
Planning
   ↓
Parallel asset generation
   ↓
Code generation → Validation → Review → Repair
   ↓
Preview → Revision → Export / Publish
```

## Tech stack

| Area | Technologies |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy |
| AI orchestration | LangGraph, LangChain, OpenAI-compatible models |
| Retrieval | PostgreSQL 16, pgvector, reciprocal-rank fusion |
| Frontend | React, TypeScript, Vite |
| Realtime updates | Server-sent events (SSE) |
| Infrastructure | Docker Compose, Alembic |
| Testing | pytest, Vitest |

## Quick start

Requirements: Docker and Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

- Application: [http://localhost:8000](http://localhost:8000)
- API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Generated artifacts: `artifacts/`
- Published sites: `deployments/`

The default `fake` model provider is deterministic and requires no API key. To use an OpenAI-compatible model, configure these server-side variables in `.env`:

```dotenv
MODEL_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_BASE_URL=...
OPENAI_MODEL=...
```

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Run the benchmark suite with `python benchmarks/run_benchmarks.py`. Results are written to `benchmarks/results.json` and `benchmarks/RESULTS.md`.

## Project scope

Foundry currently targets local, single-user workflows. Authentication, billing, multi-tenant isolation, collaborative editing, and managed cloud deployment are not included.
