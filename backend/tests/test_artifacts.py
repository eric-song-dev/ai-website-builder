from pathlib import Path

import pytest

from backend.app.artifacts import (
    ArtifactStore,
    ArtifactValidationError,
    validate_bundle,
    validate_path,
)
from backend.app.config import Settings
from backend.app.models import CodeMode
from backend.app.schemas import GeneratedBundle, GeneratedFile


def settings(tmp_path: Path) -> Settings:
    return Settings(artifact_root=tmp_path / "artifacts", deployment_root=tmp_path / "sites")


@pytest.mark.parametrize(
    "path", ["../secret.html", "/etc/passwd.html", "ok/../../bad.js", "bad\\file.html"]
)
def test_rejects_unsafe_paths(path):
    with pytest.raises(ArtifactValidationError):
        validate_path(path)


def test_mode_allowlist_and_atomic_write(tmp_path):
    bundle = GeneratedBundle(
        files=[GeneratedFile(path="index.html", content="<!doctype html><h1>Safe</h1>")]
    )
    store = ArtifactStore(settings(tmp_path))
    manifest = store.write_version("project", 1, CodeMode.single_html, bundle)
    assert manifest["version"] == 1
    assert (tmp_path / "artifacts/project/v1/index.html").exists()
    with pytest.raises(ArtifactValidationError):
        store.write_version("project", 1, CodeMode.single_html, bundle)


def test_react_cannot_change_dependencies(tmp_path):
    bundle = GeneratedBundle(files=[GeneratedFile(path="package.json", content="{}")])
    with pytest.raises(ArtifactValidationError, match="only generate"):
        validate_bundle(bundle, CodeMode.react, settings(tmp_path))
