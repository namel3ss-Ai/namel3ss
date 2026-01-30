from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


GOLDEN_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "doctor" / "doc_golden.json"
FORBIDDEN = ("/Users/", "/home/", "C:\\", "windows", "posix", "linux", "darwin")


def _run_doc(tmp_path: Path, monkeypatch, capsys) -> str:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("N3_NATIVE", raising=False)
    monkeypatch.delenv("N3_NATIVE_LIB", raising=False)
    monkeypatch.delenv("N3_PERSIST_ROOT", raising=False)
    rc = cli_main(["doc"])
    assert rc == 0
    return capsys.readouterr().out


def test_doc_matches_golden(tmp_path: Path, monkeypatch, capsys) -> None:
    out = _run_doc(tmp_path, monkeypatch, capsys)
    expected = GOLDEN_PATH.read_text(encoding="utf-8")
    assert out == expected
    for token in FORBIDDEN:
        assert token not in out


def test_doc_native_missing_fallback(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("N3_NATIVE", "1")
    monkeypatch.setenv("N3_NATIVE_LIB", "/missing/native/library")
    rc = cli_main(["doc"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    native = payload.get("native") if isinstance(payload, dict) else {}
    assert native.get("enabled") is True
    assert native.get("available") is False
    assert native.get("artifact") == "env"
