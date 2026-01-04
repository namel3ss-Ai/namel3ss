from __future__ import annotations

from pathlib import Path


def collect_capsules(project_root: Path, modules: dict) -> list[dict]:
    capsules: list[dict] = []
    for name, info in modules.items():
        source = _capsule_source(project_root, Path(info.path))
        capsules.append({"name": name, "source": source})
    return sorted(capsules, key=lambda item: item["name"])


def _capsule_source(project_root: Path, module_path: Path) -> str:
    try:
        rel = module_path.resolve().relative_to(project_root.resolve())
    except ValueError:
        return "unknown"
    if "packages" in rel.parts:
        return "package"
    return "local"


__all__ = ["collect_capsules"]
