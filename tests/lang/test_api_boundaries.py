from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.internal_api import (
    assert_import_allowed,
    detect_boundary_violation,
    is_internal_module,
)
from namel3ss.lang.public_api import assert_public_module, is_public_module


def test_public_api_module_detection() -> None:
    assert is_public_module("namel3ss.parser")
    assert is_public_module("namel3ss.ui.manifest.actions")
    assert not is_public_module("namel3ss.ir.lowering.program")


def test_public_api_assertion_raises_for_internal_module() -> None:
    with pytest.raises(Namel3ssError):
        assert_public_module("namel3ss.ir.lowering.program")


def test_internal_api_detects_external_consumer_violation() -> None:
    violation = detect_boundary_violation(
        importer_module="plugins.chart.renderer",
        imported_module="namel3ss.ir.lowering.program",
    )
    assert violation is not None
    assert "cannot import internal module" in violation.message


def test_internal_api_allows_internal_imports() -> None:
    assert is_internal_module("namel3ss.ir.lowering.program")
    assert detect_boundary_violation(
        importer_module="namel3ss.ir.lowering.program",
        imported_module="namel3ss.ir.model",
    ) is None
    assert_import_allowed("namel3ss.ir.lowering.program", "namel3ss.ir.model")
