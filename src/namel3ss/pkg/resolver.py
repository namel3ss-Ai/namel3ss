from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.types import DependencySpec, PackageMetadata, SourceSpec
from namel3ss.pkg.versions import Semver, parse_semver


@dataclass
class Requirement:
    requested_by: str
    source: SourceSpec
    constraint_raw: str | None = None


@dataclass
class ResolutionResult:
    packages: Dict[str, PackageMetadata] = field(default_factory=dict)
    graph: Dict[str, List[str]] = field(default_factory=dict)
    requirements: Dict[str, List[Requirement]] = field(default_factory=dict)


MetadataFetcher = Callable[[SourceSpec], PackageMetadata]


def resolve_dependencies(roots: Iterable[DependencySpec], fetch_metadata: MetadataFetcher) -> ResolutionResult:
    result = ResolutionResult()
    queue: List[tuple[str, DependencySpec, List[str]]] = []
    for dep in sorted(roots, key=lambda d: d.name):
        queue.append(("(app)", dep, ["(app)"]))

    while queue:
        parent, dep, chain = queue.pop(0)
        if dep.name in chain:
            cycle = " -> ".join(chain + [dep.name])
            raise Namel3ssError(
                build_guidance_message(
                    what="Circular package dependency detected.",
                    why=f"Dependency chain forms a cycle: {cycle}.",
                    fix="Remove the cycle by extracting shared code into another package.",
                    example='use "shared" as shared',
                )
            )
        _record_requirement(result, dep, parent)
        existing = result.packages.get(dep.name)
        if existing:
            _validate_same_source(dep, existing)
            _validate_constraints(result.requirements, existing)
            _record_edge(result, parent, dep.name)
            continue

        metadata = fetch_metadata(dep.source)
        if metadata.name != dep.name:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Package name mismatch for '{dep.name}'.",
                    why=f"Source {dep.source.as_string()} declares name '{metadata.name}'.",
                    fix="Update the dependency name or use the correct source.",
                    example=f'{metadata.name} = "{dep.source.as_string()}"',
                )
            )
        result.packages[dep.name] = metadata
        _record_edge(result, parent, dep.name)
        _validate_constraints(result.requirements, metadata)
        for child in sorted(metadata.dependencies, key=lambda d: d.name):
            queue.append((dep.name, child, chain + [dep.name]))

    return result


def _record_requirement(result: ResolutionResult, dep: DependencySpec, parent: str) -> None:
    req = Requirement(requested_by=parent, source=dep.source, constraint_raw=dep.constraint_raw)
    result.requirements.setdefault(dep.name, []).append(req)


def _record_edge(result: ResolutionResult, parent: str, child: str) -> None:
    if parent == "(app)":
        result.graph.setdefault("(app)", [])
    result.graph.setdefault(parent, [])
    if child not in result.graph[parent]:
        result.graph[parent].append(child)
        result.graph[parent] = sorted(result.graph[parent])


def _validate_same_source(dep: DependencySpec, metadata: PackageMetadata) -> None:
    if dep.source.as_string() != metadata.source.as_string():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Conflicting sources for package '{dep.name}'.",
                why=f"Existing source is {metadata.source.as_string()}, but another dependency requires {dep.source.as_string()}.",
                fix="Align dependencies to use the same package source.",
                example=f'{dep.name} = "{metadata.source.as_string()}"',
            )
        )


def _validate_constraints(requirements: Dict[str, List[Requirement]], metadata: PackageMetadata) -> None:
    reqs = requirements.get(metadata.name, [])
    if not reqs:
        return
    version = _parse_metadata_version(metadata)
    conflicts = []
    for req in reqs:
        if req.constraint_raw is None:
            continue
        from namel3ss.pkg.versions import parse_constraint

        constraint = parse_constraint(req.constraint_raw)
        if not constraint.matches(version):
            conflicts.append(req)
    if conflicts:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Version conflict for package '{metadata.name}'.",
                why=_format_conflicts(metadata, version, reqs),
                fix="Update the dependency constraints to align on one version.",
                example=f'{metadata.name} = "{metadata.source.as_string()}"',
            )
        )


def _parse_metadata_version(metadata: PackageMetadata) -> Semver:
    try:
        return parse_semver(metadata.version)
    except Namel3ssError as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Package '{metadata.name}' has an invalid version.",
                why=str(err),
                fix="Update the package metadata to a valid semver version.",
                example='version: "0.1.0"',
            )
        ) from err


def _format_conflicts(metadata: PackageMetadata, version: Semver, reqs: List[Requirement]) -> str:
    parts = []
    for req in reqs:
        constraint = req.constraint_raw or "(no constraint)"
        parts.append(f"{req.requested_by} requires {constraint} from {req.source.as_string()}")
    joined = "; ".join(parts)
    return f"Resolved version is {version}, but constraints do not match: {joined}."

