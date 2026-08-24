import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from .config import Settings, get_settings
from .models import CodeMode
from .schemas import GeneratedBundle

ALLOWED_SUFFIXES = {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".json", ".svg", ".ico", ".txt"}
REACT_GENERATED_PATHS = {"src/App.tsx", "src/styles.css"}


class ArtifactValidationError(ValueError):
    pass


def validate_path(path: str) -> PurePosixPath:
    candidate = PurePosixPath(path)
    if not path or candidate.is_absolute() or ".." in candidate.parts or "\\" in path:
        raise ArtifactValidationError(f"Unsafe artifact path: {path!r}")
    if candidate.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ArtifactValidationError(f"Unsupported artifact type: {path!r}")
    return candidate


def validate_bundle(
    bundle: GeneratedBundle, mode: CodeMode, settings: Settings | None = None
) -> None:
    settings = settings or get_settings()
    if not bundle.files or len(bundle.files) > settings.max_files:
        raise ArtifactValidationError("Artifact file count is outside the allowed range")
    seen: set[str] = set()
    total = 0
    for file in bundle.files:
        path = str(validate_path(file.path))
        if path in seen:
            raise ArtifactValidationError(f"Duplicate artifact path: {path}")
        if mode == CodeMode.react and path not in REACT_GENERATED_PATHS:
            raise ArtifactValidationError(
                f"React mode may only generate {sorted(REACT_GENERATED_PATHS)}"
            )
        seen.add(path)
        size = len(file.content.encode("utf-8"))
        if size > settings.max_file_bytes:
            raise ArtifactValidationError(f"Artifact file too large: {path}")
        total += size
    if total > settings.max_bundle_bytes:
        raise ArtifactValidationError("Artifact bundle is too large")
    if mode == CodeMode.single_html and seen != {"index.html"}:
        raise ArtifactValidationError("Single HTML mode must contain only index.html")
    if mode == CodeMode.multi_page and "index.html" not in seen:
        raise ArtifactValidationError("Multi-page mode requires index.html")


class ArtifactStore:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.root = self.settings.artifact_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def version_dir(self, project_id: uuid.UUID | str, version: int) -> Path:
        return self.root / str(project_id) / f"v{version}"

    def public_dir(self, project_id: uuid.UUID | str, version: int) -> Path:
        version_dir = self.version_dir(project_id, version)
        marker = version_dir / ".preview-root"
        return version_dir / marker.read_text().strip() if marker.exists() else version_dir

    def write_version(
        self, project_id: uuid.UUID | str, version: int, mode: CodeMode, bundle: GeneratedBundle
    ) -> dict:
        validate_bundle(bundle, mode, self.settings)
        project_root = self.root / str(project_id)
        project_root.mkdir(parents=True, exist_ok=True)
        target = self.version_dir(project_id, version)
        if target.exists():
            raise ArtifactValidationError(f"Version {version} already exists")
        stage = Path(tempfile.mkdtemp(prefix=f".v{version}-", dir=project_root))
        try:
            if mode == CodeMode.react:
                template = Path("templates/react-vite").resolve()
                shutil.copytree(
                    template,
                    stage,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("node_modules", "dist"),
                )
                os.symlink(template / "node_modules", stage / "node_modules", target_is_directory=True)
            for generated in bundle.files:
                relative = validate_path(generated.path)
                destination = stage.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(generated.content, encoding="utf-8")
            preview_root = "."
            if mode == CodeMode.react:
                result = subprocess.run(
                    ["node", "node_modules/vite/bin/vite.js", "build"],
                    cwd=stage,
                    capture_output=True,
                    text=True,
                    timeout=90,
                    check=False,
                )
                if result.returncode:
                    raise ArtifactValidationError(f"React build failed: {result.stderr[-1200:]}")
                preview_root = "dist"
            (stage / ".preview-root").write_text(preview_root, encoding="utf-8")
            manifest_files = []
            for path in sorted(
                p for p in stage.rglob("*") if p.is_file() and "node_modules" not in p.parts
            ):
                relative = path.relative_to(stage).as_posix()
                if relative == ".preview-root":
                    continue
                content = path.read_bytes()
                manifest_files.append(
                    {
                        "path": relative,
                        "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                )
            manifest = {
                "version": version,
                "entrypoint": bundle.entrypoint,
                "files": manifest_files,
            }
            (stage / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            os.replace(stage, target)
            return manifest
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise

    def zip_version(self, project_id: uuid.UUID | str, version: int) -> Path:
        source = self.version_dir(project_id, version)
        if not source.exists():
            raise FileNotFoundError(source)
        fd, tmp_name = tempfile.mkstemp(prefix=f"site-v{version}-", suffix=".zip")
        os.close(fd)
        archive = Path(tmp_name)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for path in source.rglob("*"):
                if path.is_file() and "node_modules" not in path.parts:
                    output.write(path, path.relative_to(source))
        return archive
