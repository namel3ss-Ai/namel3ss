from __future__ import annotations

import pytest

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError


def test_determinism_defaults(tmp_path) -> None:
    cfg = load_config(root=tmp_path)
    assert cfg.determinism.seed is None
    assert cfg.determinism.explain is True
    assert cfg.determinism.redact_user_data is False


def test_determinism_toml_values(tmp_path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text(
        (
            "[determinism]\n"
            "seed = 42\n"
            "explain = true\n"
            "redact_user_data = true\n"
        ),
        encoding="utf-8",
    )
    cfg = load_config(root=tmp_path)
    assert cfg.determinism.seed == 42
    assert cfg.determinism.explain is True
    assert cfg.determinism.redact_user_data is True


def test_determinism_env_overrides(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("N3_DETERMINISM_SEED", "run-a")
    monkeypatch.setenv("N3_EXPLAIN", "false")
    monkeypatch.setenv("N3_REDACT_USER_DATA", "true")
    cfg = load_config(root=tmp_path)
    assert cfg.determinism.seed == "run-a"
    assert cfg.determinism.explain is False
    assert cfg.determinism.redact_user_data is True


def test_determinism_invalid_toml_seed_type_rejected(tmp_path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text("[determinism]\nseed = false\n", encoding="utf-8")
    with pytest.raises(Namel3ssError) as exc:
        load_config(root=tmp_path)
    assert "determinism.seed" in exc.value.message
