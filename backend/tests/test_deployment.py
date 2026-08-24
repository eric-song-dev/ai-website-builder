from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.artifacts import ArtifactStore
from backend.app.config import Settings
from backend.app.deployment import DeploymentStore
from backend.app.models import CodeMode
from backend.app.schemas import GeneratedBundle, GeneratedFile


def test_versioned_deployment_and_collision(tmp_path: Path):
    config = Settings(
        artifact_root=tmp_path / "artifacts",
        deployment_root=tmp_path / "sites",
        public_base_url="http://test",
    )
    artifacts = ArtifactStore(config)
    project_id = uuid4()
    artifacts.write_version(
        project_id,
        1,
        CodeMode.single_html,
        GeneratedBundle(
            files=[GeneratedFile(path="index.html", content="<!doctype html><h1>Live</h1>")]
        ),
    )
    deployments = DeploymentStore(artifacts, config)
    slug, url = deployments.deploy(project_id, "My Site", 1)
    assert (tmp_path / "sites" / slug / "index.html").exists()
    assert url == f"http://test/sites/{slug}/"
    with pytest.raises(FileExistsError):
        deployments.deploy(project_id, "My Site", 1)
