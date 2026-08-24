import asyncio
import uuid

from .artifacts import ArtifactStore
from .generator import revise_bundle
from .llm import ModelGateway
from .models import CodeMode, JobStatus
from .rag import KnowledgeBase
from .repository import (
    add_event,
    complete_revision,
    get_project,
    next_version,
    promote_version,
    set_job_status,
)
from .schemas import GeneratedBundle, GeneratedFile
from .workflow import build_workflow


class JobRunner:
    def __init__(self, kb: KnowledgeBase, artifact_store: ArtifactStore):
        self.kb = kb
        self.artifacts = artifact_store
        self.gateway = ModelGateway()
        self.tasks: set[asyncio.Task] = set()

    def start(self, job_id: uuid.UUID) -> None:
        task = asyncio.create_task(self.run(job_id))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def emit(self, job_id: uuid.UUID, event: str, data: dict) -> None:
        await asyncio.to_thread(add_event, job_id, event, data)

    async def run(self, job_id: uuid.UUID) -> None:
        from .repository import get_job

        job = await asyncio.to_thread(get_job, job_id)
        if job is None:
            return
        await asyncio.to_thread(set_job_status, job_id, JobStatus.running)
        await self.emit(job_id, "job.started", {"kind": job.kind})
        try:
            project = await asyncio.to_thread(get_project, job.project_id)
            if project is None:
                raise LookupError("Project no longer exists")
            if job.kind == "generate":
                await self._generate(job_id, project)
            elif job.kind == "revision":
                await self._revise(job_id, project, job.input)
            else:
                raise ValueError(f"Unknown job kind: {job.kind}")
            await asyncio.to_thread(set_job_status, job_id, JobStatus.succeeded)
            await self.emit(job_id, "job.completed", {"status": "succeeded"})
        except Exception as exc:  # noqa: BLE001 - job boundary must persist every failure
            await asyncio.to_thread(set_job_status, job_id, JobStatus.failed, str(exc))
            await self.emit(job_id, "job.failed", {"error": str(exc)})

    async def _generate(self, job_id, project) -> None:
        async def emit(event: str, data: dict):
            await self.emit(job_id, event, data)

        graph = build_workflow(self.kb, self.gateway, emit)
        result = await graph.ainvoke(
            {"prompt": project.prompt, "mode": project.mode, "assets": [], "rounds": 0},
            config={"max_concurrency": 4, "recursion_limit": 20},
        )
        version = await asyncio.to_thread(next_version, project.id)
        manifest = await asyncio.to_thread(
            self.artifacts.write_version, project.id, version, project.mode, result["bundle"]
        )
        await asyncio.to_thread(promote_version, project.id, version, manifest)
        await self.emit(job_id, "artifact.ready", {"version": version, "manifest": manifest})

    def _read_bundle(self, project) -> GeneratedBundle:
        if project.active_version is None:
            raise ValueError("Generate a site before requesting a revision")
        root = self.artifacts.version_dir(project.id, project.active_version)
        paths = {
            CodeMode.single_html: ["index.html"],
            CodeMode.multi_page: [
                "index.html",
                "about.html",
                "contact.html",
                "assets/styles.css",
                "assets/app.js",
            ],
            CodeMode.react: ["src/App.tsx", "src/styles.css"],
        }[project.mode]
        return GeneratedBundle(
            files=[
                GeneratedFile(path=path, content=(root / path).read_text(encoding="utf-8"))
                for path in paths
            ]
        )

    async def _revise(self, job_id, project, input_data: dict) -> None:
        await self.emit(job_id, "agent.started", {"agent": "Revision"})
        current = await asyncio.to_thread(self._read_bundle, project)
        revised = revise_bundle(
            current, project.mode, input_data["instruction"], input_data.get("selected_element")
        )
        await self.emit(
            job_id,
            "artifact.patch",
            {"files": [file.path for file in revised.files], "effective": True},
        )
        version = await asyncio.to_thread(next_version, project.id)
        manifest = await asyncio.to_thread(
            self.artifacts.write_version, project.id, version, project.mode, revised
        )
        await asyncio.to_thread(promote_version, project.id, version, manifest)
        revision_id = input_data.get("revision_id")
        if revision_id:
            await asyncio.to_thread(complete_revision, uuid.UUID(revision_id), version)
        await self.emit(job_id, "agent.completed", {"agent": "Revision", "version": version})
        await self.emit(job_id, "artifact.ready", {"version": version, "manifest": manifest})
