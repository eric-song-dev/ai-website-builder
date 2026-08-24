import asyncio
import json
import mimetypes
import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse

from .artifacts import ArtifactStore
from .deployment import DeploymentStore
from .jobs import JobRunner
from .models import JobStatus
from .repository import (
    create_job,
    create_project,
    create_revision,
    get_events,
    get_job,
    get_project,
    list_projects,
    record_deployment,
)
from .schemas import DeploymentOut, JobOut, ProjectCreate, ProjectOut, RevisionCreate

router = APIRouter(prefix="/api")


def services(request: Request) -> tuple[JobRunner, ArtifactStore, DeploymentStore]:
    return request.app.state.runner, request.app.state.artifacts, request.app.state.deployments


def require_project(project_id: uuid.UUID):
    project = get_project(project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request):
    return {"status": "ready", "rag": request.app.state.kb.store is not None}


@router.post("/projects", response_model=ProjectOut, status_code=201)
def projects_create(payload: ProjectCreate):
    return create_project(payload.name, payload.prompt, payload.mode)


@router.get("/projects", response_model=list[ProjectOut])
def projects_list():
    return list_projects()


@router.get("/projects/{project_id}", response_model=ProjectOut)
def projects_get(project_id: uuid.UUID):
    return require_project(project_id)


@router.post("/projects/{project_id}/generate", response_model=JobOut, status_code=202)
async def projects_generate(project_id: uuid.UUID, request: Request):
    require_project(project_id)
    job = create_job(project_id, "generate", {})
    request.app.state.runner.start(job.id)
    return job


@router.post("/projects/{project_id}/revisions", response_model=JobOut, status_code=202)
async def projects_revise(project_id: uuid.UUID, payload: RevisionCreate, request: Request):
    project = require_project(project_id)
    if project.active_version is None:
        raise HTTPException(409, "Generate the first version before revising")
    revision = create_revision(
        project_id, payload.instruction, payload.selected_element, project.active_version
    )
    job = create_job(
        project_id,
        "revision",
        {
            "instruction": payload.instruction,
            "selected_element": payload.selected_element,
            "revision_id": str(revision.id),
        },
    )
    request.app.state.runner.start(job.id)
    return job


@router.get("/jobs/{job_id}", response_model=JobOut)
def jobs_get(job_id: uuid.UUID):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/jobs/{job_id}/events")
async def jobs_events(job_id: uuid.UUID, last_event_id: str | None = Header(None)):
    if get_job(job_id) is None:
        raise HTTPException(404, "Job not found")
    try:
        cursor = int(last_event_id or 0)
    except ValueError:
        cursor = 0

    async def stream():
        nonlocal cursor
        idle = 0
        while True:
            events = await asyncio.to_thread(get_events, job_id, cursor)
            for event in events:
                cursor = event.id
                yield f"id: {event.id}\nevent: {event.event}\ndata: {json.dumps(event.data)}\n\n"
            job = await asyncio.to_thread(get_job, job_id)
            if (
                job
                and job.status in {JobStatus.succeeded, JobStatus.failed, JobStatus.interrupted}
                and not events
            ):
                break
            idle += 1
            if idle % 40 == 0:
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.25)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/projects/{project_id}/files")
def project_files(project_id: uuid.UUID, request: Request):
    project = require_project(project_id)
    if project.active_version is None:
        return {"version": None, "files": []}
    _, artifacts, _ = services(request)
    root = artifacts.version_dir(project.id, project.active_version)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    files = []
    for item in manifest["files"]:
        path = item["path"]
        if path.startswith("dist/") or path in {"package-lock.json"}:
            continue
        file_path = root / path
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = ""
        files.append({**item, "content": content})
    return {"version": project.active_version, "entrypoint": manifest["entrypoint"], "files": files}


BRIDGE = """<script>(()=>{document.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();const el=e.target;const parts=[];let n=el;while(n&&n.nodeType===1&&parts.length<4){let p=n.tagName.toLowerCase();if(n.id)p+='#'+n.id;else if(n.classList.length)p+='.'+[...n.classList].slice(0,2).join('.');parts.unshift(p);n=n.parentElement}parent.postMessage({type:'builder:select',selector:parts.join(' > '),text:(el.innerText||el.getAttribute('alt')||'').trim().slice(0,180),path:location.pathname},'*')},true)})();</script>"""


def preview_response(project_id: uuid.UUID, path: str, request: Request):
    project = require_project(project_id)
    if project.active_version is None:
        raise HTTPException(409, "Project has no generated artifact")
    _, artifacts, _ = services(request)
    relative = PurePosixPath(path or "index.html")
    if relative.is_absolute() or ".." in relative.parts:
        raise HTTPException(400, "Unsafe preview path")
    root = artifacts.public_dir(project.id, project.active_version).resolve()
    target = root.joinpath(*relative.parts).resolve()
    if root not in target.parents and target != root:
        raise HTTPException(400, "Unsafe preview path")
    if target.is_dir():
        target = target / "index.html"
    if not target.exists():
        raise HTTPException(404, "Preview file not found")
    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    # The preview iframe intentionally has an opaque sandbox origin. ES modules
    # therefore need an explicit CORS grant even though the URL is served by
    # this application; without it, React/Vite previews render as a blank page.
    preview_headers = {"Access-Control-Allow-Origin": "*"}
    if target.suffix == ".html":
        content = target.read_text(encoding="utf-8").replace("</body>", BRIDGE + "</body>")
        return Response(
            content,
            media_type="text/html",
            headers={**preview_headers, "Cache-Control": "no-store"},
        )
    return FileResponse(target, media_type=media_type, headers=preview_headers)


@router.get("/projects/{project_id}/preview")
def project_preview_root(project_id: uuid.UUID, request: Request):
    return preview_response(project_id, "index.html", request)


@router.get("/projects/{project_id}/preview/{path:path}")
def project_preview(project_id: uuid.UUID, path: str, request: Request):
    return preview_response(project_id, path, request)


@router.get("/projects/{project_id}/export")
def project_export(project_id: uuid.UUID, request: Request):
    project = require_project(project_id)
    if project.active_version is None:
        raise HTTPException(409, "Project has no generated artifact")
    _, artifacts, _ = services(request)
    archive = artifacts.zip_version(project.id, project.active_version)
    return FileResponse(
        archive, filename=f"{project.name}-v{project.active_version}.zip", background=None
    )


@router.post("/projects/{project_id}/deploy", response_model=DeploymentOut)
def project_deploy(project_id: uuid.UUID, request: Request):
    project = require_project(project_id)
    if project.active_version is None:
        raise HTTPException(409, "Project has no generated artifact")
    _, _, deployments = services(request)
    try:
        slug, url = deployments.deploy(project.id, project.name, project.active_version)
    except FileExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    record_deployment(project.id, project.active_version, slug, url)
    return DeploymentOut(slug=slug, url=url, version=project.active_version)
