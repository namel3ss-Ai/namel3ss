from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.specification import (
    latest_spec_version,
    load_spec_registry,
    read_spec_grammar,
    resolve_spec_version,
)


def test_spec_registry_loads_and_has_latest_version() -> None:
    registry = load_spec_registry()
    versions = [item.version for item in registry.sorted_versions()]
    assert versions
    assert versions == sorted(versions, key=lambda value: tuple(int(part) for part in value.split(".")))
    latest = latest_spec_version()
    assert latest.version == versions[-1]
    assert latest.grammar_path.exists()
    assert latest.overview_path.exists()


def test_resolve_unknown_spec_version_raises() -> None:
    with pytest.raises(Namel3ssError):
        resolve_spec_version("99.99.99")


def test_read_spec_grammar_matches_version_file() -> None:
    latest = latest_spec_version()
    text = read_spec_grammar(latest.version)
    direct = Path(latest.grammar_path).read_text(encoding="utf-8")
    assert text == direct
    assert "program" in text
    assert "flow_decl" in text
