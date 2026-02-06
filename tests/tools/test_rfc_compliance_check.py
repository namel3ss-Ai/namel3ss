from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = Path("tools/rfc_compliance_check.py").resolve()
    spec = importlib.util.spec_from_file_location("rfc_compliance_check", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_language_surface_detection() -> None:
    module = _load_module()
    assert module._is_language_surface("src/namel3ss/parser/parse_program.py")
    assert module._is_language_surface("src/namel3ss/lexer/lexer.py")
    assert module._is_language_surface("spec/grammar/namel3ss.grammar")
    assert not module._is_language_surface("docs/quickstart.md")


def test_main_requires_approval_for_language_changes(monkeypatch, capsys) -> None:
    module = _load_module()

    monkeypatch.setattr(module, "_load_event", lambda: None)
    monkeypatch.setattr(module, "_changed_files", lambda _event: ["src/namel3ss/parser/decl/flow.py"])
    monkeypatch.setattr(module, "_event_labels", lambda _event: set())
    monkeypatch.delenv("N3_RFC_ID", raising=False)
    monkeypatch.delenv("RFC_ID", raising=False)

    rc = module.main()
    output = capsys.readouterr().out

    assert rc == 1
    assert "require an accepted RFC" in output


def test_main_accepts_env_rfc_id(monkeypatch, capsys) -> None:
    module = _load_module()

    monkeypatch.setattr(module, "_load_event", lambda: None)
    monkeypatch.setattr(module, "_changed_files", lambda _event: ["src/namel3ss/lang/keywords.py"])
    monkeypatch.setattr(module, "_event_labels", lambda _event: set())
    monkeypatch.setenv("N3_RFC_ID", "RFC-1234")

    rc = module.main()
    output = capsys.readouterr().out

    assert rc == 0
    assert "allowed" in output
    assert "RFC-1234" in output
