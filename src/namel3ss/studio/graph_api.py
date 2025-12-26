from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project
from namel3ss.pkg.lockfile import read_lockfile


def get_graph_payload(app_path: str) -> dict:
    app_file = Path(app_path)
    project = load_project(app_file)
    project_root = project.app_path.parent
    packages = _load_lock_packages(project_root)

    nodes: list[dict] = []
    node_ids: dict[str, str] = {}

    app_node = {
        "id": "app",
        "name": "app",
        "type": "app",
        "source": _rel_path(project.app_path, project_root),
        "exports": {},
    }
    nodes.append(app_node)
    node_ids["(app)"] = "app"

    for name, info in sorted(project.modules.items()):
        module_type = _module_type(info.path)
        node_id = f"{module_type}:{name}"
        node = {
            "id": node_id,
            "name": name,
            "type": module_type,
            "source": _module_source(info.path, project_root, packages.get(name)),
            "exports": _normalize_exports(info.exports.kinds()),
        }
        if module_type == "package":
            pkg = packages.get(name)
            node["version"] = getattr(pkg, "version", None)
            node["license"] = getattr(pkg, "license_id", None) or getattr(pkg, "license_file", None)
        nodes.append(node)
        node_ids[name] = node_id

    edges = []
    for src, dst in project.graph.edges:
        src_id = node_ids.get(src)
        dst_id = node_ids.get(dst)
        if not src_id or not dst_id:
            continue
        edges.append({"from": src_id, "to": dst_id})

    nodes = sorted(nodes, key=lambda item: item.get("id", ""))
    edges = sorted(edges, key=lambda item: (item.get("from", ""), item.get("to", "")))
    return {"schema_version": 1, "nodes": nodes, "edges": edges}


def get_exports_payload(app_path: str) -> dict:
    app_file = Path(app_path)
    project = load_project(app_file)
    project_root = project.app_path.parent
    packages = _load_lock_packages(project_root)

    capsules: list[dict] = []
    for name, info in sorted(project.modules.items()):
        module_type = _module_type(info.path)
        entry = {
            "name": name,
            "type": module_type,
            "source": _module_source(info.path, project_root, packages.get(name)),
            "exports": _normalize_exports(info.exports.kinds()),
        }
        if module_type == "package":
            pkg = packages.get(name)
            entry["version"] = getattr(pkg, "version", None)
            entry["license"] = getattr(pkg, "license_id", None) or getattr(pkg, "license_file", None)
        capsules.append(entry)
    return {"schema_version": 1, "capsules": capsules}


def _load_lock_packages(project_root: Path) -> dict[str, object]:
    try:
        lock = read_lockfile(project_root)
    except Namel3ssError:
        return {}
    return {pkg.name: pkg for pkg in lock.packages}


def _module_type(path: Path) -> str:
    parent = path.parent.name
    if parent == "packages":
        return "package"
    if parent == "modules":
        return "capsule"
    return "capsule"


def _module_source(path: Path, project_root: Path, pkg: object | None) -> str | None:
    if pkg is not None and hasattr(pkg, "source"):
        source = getattr(pkg, "source")
        if hasattr(source, "as_string"):
            return source.as_string()
    return _rel_path(path, project_root)


def _rel_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _normalize_exports(exports: dict) -> dict:
    normalized: dict[str, list[str]] = {}
    for kind in sorted(exports.keys()):
        names = exports.get(kind) or []
        normalized[kind] = sorted(list(names))
    return normalized


__all__ = ["get_graph_payload", "get_exports_payload"]
