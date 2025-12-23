from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.pkg.resolver import resolve_dependencies
from namel3ss.pkg.types import DependencySpec, PackageMetadata, SourceSpec


def _source(name: str, ref: str) -> SourceSpec:
    return SourceSpec(scheme="github", owner="owner", repo=name, ref=ref)


def _meta(name: str, version: str, deps=None) -> PackageMetadata:
    deps = deps or []
    return PackageMetadata(
        name=name,
        version=version,
        source=_source(name, f"v{version}"),
        license_id="MIT",
        license_file=None,
        checksums_file="checksums.json",
        dependencies=deps,
    )


def test_resolver_collects_transitive_dependencies():
    inventory = _meta(
        "inventory",
        "0.1.0",
        deps=[DependencySpec(name="shared", source=_source("shared", "v0.1.0"))],
    )
    shared = _meta("shared", "0.1.0")
    catalog = {
        inventory.source.as_string(): inventory,
        shared.source.as_string(): shared,
    }

    def fetch(source):
        return catalog[source.as_string()]

    roots = [DependencySpec(name="inventory", source=inventory.source)]
    result = resolve_dependencies(roots, fetch)
    assert set(result.packages.keys()) == {"inventory", "shared"}
    assert result.graph["inventory"] == ["shared"]


def test_resolver_conflicting_source():
    inventory = _meta(
        "inventory",
        "0.1.0",
        deps=[DependencySpec(name="shared", source=_source("shared", "v0.1.0"))],
    )
    shared = _meta("shared", "0.1.0")
    alt_shared = _meta("shared", "0.1.0")
    alt_shared.source = _source("shared-alt", "v0.1.0")

    catalog = {
        inventory.source.as_string(): inventory,
        shared.source.as_string(): shared,
        alt_shared.source.as_string(): alt_shared,
    }

    def fetch(source):
        return catalog[source.as_string()]

    roots = [
        DependencySpec(name="inventory", source=inventory.source),
        DependencySpec(name="shared", source=alt_shared.source),
    ]
    with pytest.raises(Namel3ssError) as excinfo:
        resolve_dependencies(roots, fetch)
    assert "conflicting sources" in str(excinfo.value).lower()


def test_resolver_constraint_conflict():
    shared = _meta("shared", "0.2.0")
    catalog = {shared.source.as_string(): shared}

    def fetch(source):
        return catalog[source.as_string()]

    dep = DependencySpec(name="shared", source=shared.source, constraint_raw="=0.1.0")
    with pytest.raises(Namel3ssError) as excinfo:
        resolve_dependencies([dep], fetch)
    assert "version conflict" in str(excinfo.value).lower()


def test_resolver_cycle_detection():
    alpha = _meta("alpha", "0.1.0")
    beta = _meta("beta", "0.1.0")
    alpha.dependencies = [DependencySpec(name="beta", source=beta.source)]
    beta.dependencies = [DependencySpec(name="alpha", source=alpha.source)]
    catalog = {
        alpha.source.as_string(): alpha,
        beta.source.as_string(): beta,
    }

    def fetch(source):
        return catalog[source.as_string()]

    with pytest.raises(Namel3ssError) as excinfo:
        resolve_dependencies([DependencySpec(name="alpha", source=alpha.source)], fetch)
    assert "cycle" in str(excinfo.value).lower()
