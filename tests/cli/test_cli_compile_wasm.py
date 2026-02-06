from __future__ import annotations

import hashlib
import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


PURE_APP = '''spec is "1.0"

contract flow "add":
  input:
    a is number
    b is number
  output:
    result is number

flow "add": purity is "pure"
  let total is input.a + input.b
  return total
'''


EFFECTFUL_APP = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def test_cli_compile_generates_deterministic_sources(tmp_path: Path, capsys, monkeypatch) -> None:
    app = tmp_path / "app.ai"
    app.write_text(PURE_APP, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli_main(["compile", "--lang", "c", "--flow", "add", "--out", "dist", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["language"] == "c"
    assert payload["source_only"] is True

    source_path = tmp_path / "dist" / "add" / "c" / "add.c"
    assert source_path.exists()
    first_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()

    assert cli_main(["compile", "--lang", "c", "--flow", "add", "--out", "dist", "--json"]) == 0
    payload_two = json.loads(capsys.readouterr().out)
    assert payload_two["ok"] is True
    second_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()

    assert first_hash == second_hash


def test_cli_compile_list_and_clean(tmp_path: Path, capsys, monkeypatch) -> None:
    app = tmp_path / "app.ai"
    app.write_text(PURE_APP, encoding="utf-8")
    (tmp_path / "compilation.yaml").write_text("flows:\n  add: rust\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli_main(["compile", "list", "--json"]) == 0
    list_payload = json.loads(capsys.readouterr().out)
    assert list_payload["count"] == 1
    assert list_payload["items"][0]["flow_name"] == "add"
    assert list_payload["items"][0]["target"] == "rust"

    assert cli_main(["compile", "--lang", "rust", "--flow", "add", "--out", "dist", "--json"]) == 0
    compile_payload = json.loads(capsys.readouterr().out)
    assert compile_payload["ok"] is True

    assert cli_main(["compile", "clean", "--out", "dist", "--json"]) == 0
    clean_payload = json.loads(capsys.readouterr().out)
    assert clean_payload["removed"] is True
    assert clean_payload["files_removed"] >= 1


def test_cli_compile_rejects_non_pure_flow(tmp_path: Path, capsys, monkeypatch) -> None:
    app = tmp_path / "app.ai"
    app.write_text(EFFECTFUL_APP, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli_main(["compile", "--lang", "c", "--flow", "demo"]) == 1
    err = capsys.readouterr().err
    assert "pure" in err.lower()


def test_cli_wasm_run_requires_runtime(tmp_path: Path, capsys, monkeypatch) -> None:
    module_path = tmp_path / "module.wasm"
    module_path.write_bytes(b"00asm")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "")

    assert cli_main(["wasm", "run", module_path.as_posix(), "--input", "{}", "--json"]) == 1
    err = capsys.readouterr().err
    assert "wasm runtime" in err.lower()
