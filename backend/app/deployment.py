import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

from .artifacts import ArtifactStore
from .config import Settings, get_settings


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:60] or "site"


class DeploymentStore:
    def __init__(self, artifacts: ArtifactStore, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.artifacts = artifacts
        self.root = self.settings.deployment_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def deploy(self, project_id: uuid.UUID, project_name: str, version: int) -> tuple[str, str]:
        source = self.artifacts.public_dir(project_id, version)
        slug = f"{slugify(project_name)}-{str(project_id)[:8]}-v{version}"
        target = self.root / slug
        if target.exists():
            raise FileExistsError(f"Deployment slug already exists: {slug}")
        stage = Path(tempfile.mkdtemp(prefix=f".{slug}-", dir=self.root))
        try:
            shutil.copytree(source, stage, dirs_exist_ok=True)
            os.replace(stage, target)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        return slug, f"{self.settings.public_base_url.rstrip('/')}/sites/{slug}/"
