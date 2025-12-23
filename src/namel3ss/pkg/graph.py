from __future__ import annotations

from typing import Dict, List

from namel3ss.pkg.types import Lockfile


def build_dependency_map(lockfile: Lockfile) -> Dict[str, List[str]]:
    deps: Dict[str, List[str]] = {}
    for pkg in lockfile.packages:
        deps[pkg.name] = sorted({dep.name for dep in pkg.dependencies})
    return deps


def tree_lines(lockfile: Lockfile) -> List[str]:
    versions = {pkg.name: pkg.version for pkg in lockfile.packages}
    deps = build_dependency_map(lockfile)
    roots = sorted({root.name for root in lockfile.roots})
    lines: List[str] = []
    for root in roots:
        if root not in versions:
            continue
        lines.append(f"{root} {versions[root]}")
        _walk_tree(root, deps, versions, prefix="  ", lines=lines, seen=set())
    return lines


def why_paths(lockfile: Lockfile, target: str) -> List[List[str]]:
    deps = build_dependency_map(lockfile)
    roots = sorted({root.name for root in lockfile.roots})
    paths: List[List[str]] = []
    for root in roots:
        _walk_paths(root, target, deps, path=[root], paths=paths)
    return paths


def _walk_tree(
    node: str,
    deps: Dict[str, List[str]],
    versions: Dict[str, str],
    *,
    prefix: str,
    lines: List[str],
    seen: set[str],
) -> None:
    if node in seen:
        return
    seen.add(node)
    for child in deps.get(node, []):
        if child not in versions:
            continue
        lines.append(f"{prefix}- {child} {versions[child]}")
        _walk_tree(child, deps, versions, prefix=prefix + "  ", lines=lines, seen=seen)


def _walk_paths(
    node: str,
    target: str,
    deps: Dict[str, List[str]],
    *,
    path: List[str],
    paths: List[List[str]],
) -> None:
    if node == target:
        paths.append(list(path))
        return
    for child in deps.get(node, []):
        if child in path:
            continue
        _walk_paths(child, target, deps, path=path + [child], paths=paths)
