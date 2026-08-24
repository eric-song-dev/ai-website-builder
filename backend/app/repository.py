import uuid

from sqlalchemy import func, select

from .db import session_scope
from .models import ArtifactVersion, Deployment, Job, JobEvent, JobStatus, Project, Revision


def create_project(name: str, prompt: str, mode) -> Project:
    with session_scope() as session:
        project = Project(name=name, prompt=prompt, mode=mode)
        session.add(project)
        session.flush()
        return project


def list_projects() -> list[Project]:
    with session_scope() as session:
        return list(session.scalars(select(Project).order_by(Project.updated_at.desc())))


def get_project(project_id: uuid.UUID) -> Project | None:
    with session_scope() as session:
        return session.get(Project, project_id)


def create_job(project_id: uuid.UUID, kind: str, input_data: dict) -> Job:
    with session_scope() as session:
        job = Job(project_id=project_id, kind=kind, input=input_data, status=JobStatus.queued)
        session.add(job)
        session.flush()
        return job


def get_job(job_id: uuid.UUID) -> Job | None:
    with session_scope() as session:
        return session.get(Job, job_id)


def set_job_status(job_id: uuid.UUID, status: JobStatus, error: str | None = None) -> None:
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job:
            job.status = status
            job.error = error


def add_event(job_id: uuid.UUID, event: str, data: dict) -> JobEvent:
    with session_scope() as session:
        item = JobEvent(job_id=job_id, event=event, data=data)
        session.add(item)
        session.flush()
        return item


def get_events(job_id: uuid.UUID, after: int = 0) -> list[JobEvent]:
    with session_scope() as session:
        return list(
            session.scalars(
                select(JobEvent)
                .where(JobEvent.job_id == job_id, JobEvent.id > after)
                .order_by(JobEvent.id)
            )
        )


def next_version(project_id: uuid.UUID) -> int:
    with session_scope() as session:
        maximum = session.scalar(
            select(func.coalesce(func.max(ArtifactVersion.number), 0)).where(
                ArtifactVersion.project_id == project_id
            )
        )
        return int(maximum or 0) + 1


def promote_version(project_id: uuid.UUID, number: int, manifest: dict) -> ArtifactVersion:
    with session_scope() as session:
        version = ArtifactVersion(
            project_id=project_id, number=number, manifest=manifest, status="stable"
        )
        session.add(version)
        project = session.get(Project, project_id)
        if project is None:
            raise LookupError(project_id)
        project.active_version = number
        session.flush()
        return version


def create_revision(
    project_id: uuid.UUID, instruction: str, selected: dict | None, from_version: int
) -> Revision:
    with session_scope() as session:
        revision = Revision(
            project_id=project_id,
            instruction=instruction,
            selected_element=selected,
            from_version=from_version,
        )
        session.add(revision)
        session.flush()
        return revision


def complete_revision(revision_id: uuid.UUID, to_version: int) -> None:
    with session_scope() as session:
        revision = session.get(Revision, revision_id)
        if revision:
            revision.to_version = to_version


def record_deployment(project_id: uuid.UUID, version: int, slug: str, url: str) -> Deployment:
    with session_scope() as session:
        deployment = Deployment(project_id=project_id, version=version, slug=slug, url=url)
        session.add(deployment)
        session.flush()
        return deployment
