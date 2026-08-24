import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import CodeMode, JobStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=10, max_length=10_000)
    mode: CodeMode


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    prompt: str
    mode: CodeMode
    active_version: int | None
    created_at: datetime
    updated_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    kind: str
    status: JobStatus
    error: str | None
    created_at: datetime
    updated_at: datetime


class RevisionCreate(BaseModel):
    instruction: str = Field(min_length=2, max_length=4_000)
    selected_element: dict | None = None


class GeneratedFile(BaseModel):
    path: str
    content: str


class GeneratedBundle(BaseModel):
    files: list[GeneratedFile]
    entrypoint: str = "index.html"


class SitePlan(BaseModel):
    title: str
    audience: str
    pages: list[str]
    sections: list[str]
    tone: str
    palette: list[str]


class ReviewResult(BaseModel):
    approved: bool
    issues: list[str] = []
    score: int = Field(ge=0, le=100)


class FileManifest(BaseModel):
    version: int
    entrypoint: str
    files: list[dict]


class DeploymentOut(BaseModel):
    slug: str
    url: str
    version: int


EventName = Literal[
    "job.started",
    "agent.started",
    "agent.completed",
    "asset.completed",
    "artifact.patch",
    "artifact.ready",
    "job.completed",
    "job.failed",
]
