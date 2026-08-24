from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import router
from .artifacts import ArtifactStore
from .config import get_settings
from .db import mark_interrupted_jobs
from .deployment import DeploymentStore
from .jobs import JobRunner
from .rag import KnowledgeBase

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.artifact_root.mkdir(parents=True, exist_ok=True)
    settings.deployment_root.mkdir(parents=True, exist_ok=True)
    mark_interrupted_jobs()
    try:
        app.state.kb.initialize()
    except Exception as exc:  # noqa: BLE001 - local retrieval remains available
        app.state.rag_warning = str(exc)
    yield


app = FastAPI(title="AI Website Builder", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.kb = KnowledgeBase(settings)
app.state.artifacts = ArtifactStore(settings)
app.state.deployments = DeploymentStore(app.state.artifacts, settings)
app.state.runner = JobRunner(app.state.kb, app.state.artifacts)
app.include_router(router)

app.mount("/sites", StaticFiles(directory=settings.deployment_root, html=True), name="sites")
frontend_dist = Path("frontend/dist")
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
