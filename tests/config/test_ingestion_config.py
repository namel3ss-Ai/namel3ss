from __future__ import annotations

import pytest

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError


def test_ingestion_config_defaults(tmp_path) -> None:
    cfg = load_config(root=tmp_path)
    assert cfg.ingestion.enable_diagnostics is True
    assert cfg.ingestion.enable_ocr_fallback is True


def test_ingestion_config_toml_values(tmp_path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text(
        (
            "[ingestion]\n"
            "enable_diagnostics = false\n"
            "enable_ocr_fallback = false\n"
        ),
        encoding="utf-8",
    )
    cfg = load_config(root=tmp_path)
    assert cfg.ingestion.enable_diagnostics is False
    assert cfg.ingestion.enable_ocr_fallback is False


def test_ingestion_config_rejects_non_boolean_values(tmp_path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text("[ingestion]\nenable_diagnostics = \"no\"\n", encoding="utf-8")
    with pytest.raises(Namel3ssError) as exc:
        load_config(root=tmp_path)
    assert "ingestion.enable_diagnostics" in exc.value.message
