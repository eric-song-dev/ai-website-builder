from contextlib import contextmanager

from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import Job, JobStatus

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope():
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def mark_interrupted_jobs() -> None:
    with session_scope() as session:
        session.execute(
            update(Job)
            .where(Job.status.in_([JobStatus.queued, JobStatus.running]))
            .values(status=JobStatus.interrupted, error="Application restarted before completion")
        )
