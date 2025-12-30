from __future__ import annotations

from pathlib import Path
from typing import List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.graph import tree_lines, why_paths
from namel3ss.pkg.index import get_entry, load_index, search_index
from namel3ss.pkg.install import FetchSession, install_from_resolution, lockfile_from_resolution
from namel3ss.pkg.lockfile import read_lockfile, write_lockfile
from namel3ss.pkg.manager import resolve_project
from namel3ss.pkg.manifest import load_manifest_optional, write_manifest
from namel3ss.pkg.plan import diff_lockfiles, plan_to_dict
from namel3ss.pkg.specs import parse_source_spec
from namel3ss.pkg.types import DependencySpec
from namel3ss.pkg.validate import validate_package
from namel3ss.pkg.verify import verify_installation
from namel3ss.utils.json_tools import dumps_pretty


def run_pkg(args: List[str]) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    cmd = args[0]
    json_mode = "--json" in args
    strict_mode = "--strict" in args
    args = [arg for arg in args if arg not in {"--json", "--strict"}]
    root = Path.cwd()
    if cmd in {"add", "install", "plan", "tree", "why", "verify", "licenses"}:
        _require_project_root(root)

    if cmd == "add":
        if len(args) < 2:
            raise Namel3ssError(
                build_guidance_message(
                    what="Package spec is missing.",
                    why="`n3 pkg add` requires a GitHub source spec or index name.",
                    fix="Provide github:owner/repo@ref or a known package name.",
                    example="n3 pkg add auth-basic",
                )
            )
        return _run_add(root, args[1], json_mode)
    if cmd == "search":
        if len(args) < 2:
            raise Namel3ssError(
                build_guidance_message(
                    what="Search query is missing.",
                    why="`n3 pkg search` needs a query string.",
                    fix="Provide a keyword to search the index.",
                    example="n3 pkg search auth",
                )
            )
        return _run_search(args[1], json_mode)
    if cmd == "info":
        if len(args) < 2:
            raise Namel3ssError(
                build_guidance_message(
                    what="Package name is missing.",
                    why="`n3 pkg info` needs a package name.",
                    fix="Provide the package name from the index.",
                    example="n3 pkg info auth-basic",
                )
            )
        return _run_info(args[1], json_mode)
    if cmd == "validate":
        target = args[1] if len(args) > 1 else "."
        return _run_validate(target, json_mode, strict_mode)
    if cmd == "install":
        return _run_install(root, json_mode)
    if cmd == "plan":
        return _run_plan(root, json_mode)
    if cmd == "tree":
        return _run_tree(root, json_mode)
    if cmd == "why":
        if len(args) < 2:
            raise Namel3ssError(
                build_guidance_message(
                    what="Package name is missing.",
                    why="`n3 pkg why` needs a package name.",
                    fix="Provide the package name to inspect.",
                    example="n3 pkg why inventory",
                )
            )
        return _run_why(root, args[1], json_mode)
    if cmd == "verify":
        return _run_verify(root, json_mode)
    if cmd == "licenses":
        return _run_licenses(root, json_mode)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown pkg command '{cmd}'.",
            why="Supported commands are add, install, plan, tree, why, verify, and licenses.",
            fix="Run `n3 pkg help` to see usage.",
            example="n3 pkg help",
        )
    )


def _require_project_root(root: Path) -> None:
    if not (root / "app.ai").exists():
        raise Namel3ssError(
            build_guidance_message(
                what="app.ai was not found.",
                why="Package commands run from a project root containing app.ai.",
                fix="Change to your project directory and retry.",
                example="cd my_app",
            )
        )


def _run_add(root: Path, spec_text: str, json_mode: bool) -> int:
    source = _resolve_source_spec(spec_text)
    manifest = load_manifest_optional(root)
    session = FetchSession()
    try:
        metadata = _fetch_metadata_for_source(session, source)
        dep_name = metadata.name
        existing = manifest.dependencies.get(dep_name)
        if existing and existing.source.as_string() != source.as_string():
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Dependency '{dep_name}' is already declared with a different source.",
                    why=f"Existing source is {existing.source.as_string()}.",
                    fix="Remove the existing dependency or use the same source.",
                    example=f'{dep_name} = "{existing.source.as_string()}"',
                )
            )
        manifest.dependencies[dep_name] = DependencySpec(name=dep_name, source=source)
        write_manifest(root, manifest)

        current = _read_lockfile_optional(root)
        manifest, resolution, session = resolve_project(root, session=session)
        lockfile = install_from_resolution(root, manifest.dependencies.values(), resolution, fetch_session=session)
        write_lockfile(root, lockfile)
        changes = diff_lockfiles(current, lockfile)
    finally:
        session.close()

    if json_mode:
        payload = {"status": "ok", "added": {"name": dep_name, "source": source.as_string()}, **plan_to_dict(changes)}
        print(dumps_pretty(payload))
        return 0

    _print_changes(changes)
    print(f"Added {dep_name} from {source.as_string()}.")
    return 0


def _run_search(query: str, json_mode: bool) -> int:
    entries = load_index()
    results = search_index(query, entries)
    if json_mode:
        payload = {
            "status": "ok",
            "query": query,
            "count": len(results),
            "results": [result.to_dict() for result in results],
        }
        print(dumps_pretty(payload))
        return 0
    if not results:
        print("No matching packages.")
        return 0
    for result in results:
        entry = result.entry
        tags = ", ".join(entry.tags)
        print(f"{entry.name} trust {entry.trust_tier} - {entry.description}")
        if tags:
            print(f"  tags: {tags}")
        print(f"  install: n3 pkg add {entry.source_spec()}")
    return 0


def _run_info(name: str, json_mode: bool) -> int:
    entries = load_index()
    entry = get_entry(name, entries)
    if entry is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Package '{name}' is not in the index.",
                why="The official index does not include that name.",
                fix="Check the spelling or use a GitHub source spec.",
                example="n3 pkg add github:owner/repo@v0.1.0",
            )
        )
    payload = entry.to_dict()
    payload["install"] = f"n3 pkg add {entry.source_spec()}"
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"{entry.name} trust {entry.trust_tier}")
    print(entry.description)
    print(f"source: {entry.source}")
    print(f"recommended: {entry.recommended}")
    print(f"license: {entry.license}")
    if entry.tags:
        print(f"tags: {', '.join(entry.tags)}")
    print(f"install: n3 pkg add {entry.source_spec()}")
    return 0


def _run_validate(target: str, json_mode: bool, strict_mode: bool) -> int:
    report = validate_package(target, strict=strict_mode)
    if json_mode:
        payload = report.to_dict()
        print(dumps_pretty(payload))
        return 0 if report.status == "ok" else 1
    if not report.issues:
        print("Package validated successfully.")
        return 0
    for issue in report.issues:
        prefix = "ERROR" if issue.severity == "error" else "WARN"
        location = f" path {issue.path}" if issue.path else ""
        print(f"{prefix}: {issue.message}{location}")
    return 0 if report.status == "ok" else 1


def _run_install(root: Path, json_mode: bool) -> int:
    current = _read_lockfile_optional(root)
    session = FetchSession()
    try:
        manifest, resolution, session = resolve_project(root, session=session)
        lockfile = install_from_resolution(root, manifest.dependencies.values(), resolution, fetch_session=session)
        write_lockfile(root, lockfile)
        changes = diff_lockfiles(current, lockfile)
    finally:
        session.close()

    if json_mode:
        payload = {"status": "ok", **plan_to_dict(changes)}
        print(dumps_pretty(payload))
        return 0
    if not changes:
        print("Packages are already up to date.")
        return 0
    _print_changes(changes)
    return 0


def _run_plan(root: Path, json_mode: bool) -> int:
    current = _read_lockfile_optional(root)
    session = FetchSession()
    try:
        manifest, resolution, session = resolve_project(root, session=session)
        next_lock = lockfile_from_resolution(manifest.dependencies.values(), resolution, fetch_session=session)
        changes = diff_lockfiles(current, next_lock)
    finally:
        session.close()

    if json_mode:
        print(dumps_pretty(plan_to_dict(changes)))
        return 0
    if not changes:
        print("No package changes.")
        return 0
    _print_changes(changes)
    return 0


def _run_tree(root: Path, json_mode: bool) -> int:
    lockfile = read_lockfile(root)
    if json_mode:
        nodes = [{"name": pkg.name, "version": pkg.version} for pkg in lockfile.packages]
        edges = [
            {"from": pkg.name, "to": dep.name}
            for pkg in lockfile.packages
            for dep in pkg.dependencies
        ]
        payload = {"roots": [dep.name for dep in lockfile.roots], "nodes": nodes, "edges": edges}
        print(dumps_pretty(payload))
        return 0
    lines = tree_lines(lockfile)
    print("\n".join(lines) if lines else "No dependencies.")
    return 0


def _run_why(root: Path, name: str, json_mode: bool) -> int:
    lockfile = read_lockfile(root)
    paths = why_paths(lockfile, name)
    if not paths:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Package '{name}' is not in the dependency tree.",
                why="The lockfile does not list this package.",
                fix="Check the package name or run `n3 pkg install`.",
                example="n3 pkg tree",
            )
        )
    if json_mode:
        payload = {"name": name, "paths": paths}
        print(dumps_pretty(payload))
        return 0
    for path in paths:
        print(" -> ".join(path))
    return 0


def _run_verify(root: Path, json_mode: bool) -> int:
    issues = verify_installation(root)
    status = "ok" if not issues else "fail"
    if json_mode:
        payload = {
            "status": status,
            "issues": [{"name": issue.name, "message": issue.message} for issue in issues],
        }
        print(dumps_pretty(payload))
        return 0 if not issues else 1
    if not issues:
        print("All packages verified.")
        return 0
    for issue in issues:
        print(f"{issue.name}: {issue.message}")
    return 1


def _run_licenses(root: Path, json_mode: bool) -> int:
    lockfile = read_lockfile(root)
    entries = []
    for pkg in sorted(lockfile.packages, key=lambda p: p.name):
        entries.append(
            {
                "name": pkg.name,
                "version": pkg.version,
                "license": pkg.license_id,
                "license_file": pkg.license_file,
            }
        )
    if json_mode:
        print(dumps_pretty({"licenses": entries}))
        return 0
    for entry in entries:
        license_value = entry["license"] or entry["license_file"] or "unknown"
        print(f'{entry["name"]} {entry["version"]} {license_value}')
    return 0


def _print_changes(changes) -> None:
    for change in changes:
        if change.kind == "add":
            print(f"ADD {change.name} {change.to_version}")
        elif change.kind == "remove":
            print(f"REMOVE {change.name} {change.from_version}")
        elif change.kind == "update":
            print(f"UPDATE {change.name} {change.from_version} -> {change.to_version}")


def _print_usage() -> None:
    usage = """Usage:
  n3 pkg add spec_or_name  # add dependency from source or index
  n3 pkg search query      # search the official index
  n3 pkg info name         # show index entry details
  n3 pkg validate path     # validate a package folder or github spec
  n3 pkg install           # install from manifest or lockfile
  n3 pkg plan              # preview changes
  n3 pkg tree              # show dependency tree
  n3 pkg why name          # explain why a package is installed
  n3 pkg verify            # verify checksums and licenses
  n3 pkg licenses          # list package licenses
  n3 pkg command --json    # JSON output for any command
  n3 pkg validate --strict # fail on warnings
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


def _read_lockfile_optional(root: Path):
    try:
        return read_lockfile(root)
    except Namel3ssError:
        return None


def _fetch_metadata_for_source(session: FetchSession, source) -> object:
    from namel3ss.pkg.metadata import load_metadata

    root_path = session.fetch(source)
    metadata = load_metadata(root_path)
    if metadata.source.as_string() != source.as_string():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Package source mismatch for '{metadata.name}'.",
                why=f"Metadata declares {metadata.source.as_string()}, expected {source.as_string()}.",
                fix="Use the correct source or update the package metadata.",
                example=source.as_string(),
            )
        )
    return metadata


def _resolve_source_spec(value: str):
    try:
        return parse_source_spec(value)
    except Namel3ssError:
        entries = load_index()
        entry = get_entry(value, entries)
        if entry is None:
            raise Namel3ssError(
                build_guidance_message(
                    what="Package spec is not valid.",
                    why="The value is not a GitHub source and was not found in the index.",
                    fix="Use github:owner/repo@ref or a known package name.",
                    example="n3 pkg add auth-basic",
                )
            )
        return parse_source_spec(entry.source_spec())
