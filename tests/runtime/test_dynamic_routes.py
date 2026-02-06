from __future__ import annotations

import hashlib
import io
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.persistence.local_store import LocalStore
from namel3ss.persistence.store import StoredDefinitions
from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.registry import RouteRegistry


def _program(tmp_path: Path, source: str):
    app = tmp_path / "app.ai"
    app.write_text(source, encoding="utf-8")
    program, _sources = load_program(app.as_posix())
    return program


def test_dynamic_route_dispatch_parses_params(tmp_path: Path) -> None:
    source = '''spec is "1.0"

flow "echo":
  return input.id

route "echo_route":
  path is "/api/echo/{id}"
  method is "GET"
  parameters:
    id is number
  request:
    id is number
  response:
    id is number
  flow is "echo"
'''
    program = _program(tmp_path, source)
    registry = RouteRegistry()
    registry.update(program.routes)
    result = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/echo/42",
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=None,
        auth_context=None,
        store=None,
    )
    assert result is not None
    assert result.status == 200
    assert result.payload == {"id": 42}


def test_upload_route_records_dataset(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  uploads

flow "store":
  return input.upload_id

route "upload_data":
  path is "/api/upload-data"
  method is "POST"
  request:
    upload is json
  response:
    upload_id is text
  flow is "store"
  upload is true
'''
    program = _program(tmp_path, source)
    registry = RouteRegistry()
    registry.update(program.routes)
    payload = b"name,age\nalice,30\n"
    checksum = hashlib.sha256(payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()
    headers = {
        "Content-Type": "text/csv",
        "Content-Length": str(len(payload)),
        "X-Upload-Name": "people.csv",
    }
    result = dispatch_route(
        registry=registry,
        method="POST",
        raw_path="/api/upload-data",
        headers=headers,
        rfile=io.BytesIO(payload),
        program=program,
        identity=None,
        auth_context=None,
        store=None,
    )
    assert result is not None
    assert result.payload.get("upload_id") == checksum

    store = LocalStore(tmp_path, tmp_path / "app.ai")
    datasets = store.load_datasets()
    assert any(entry.get("dataset_id") == checksum for entry in datasets)


def test_local_store_definitions_roundtrip(tmp_path: Path) -> None:
    store = LocalStore(tmp_path, tmp_path / "app.ai")
    definitions = StoredDefinitions(
        routes=[{"name": "route", "path": "/api/route", "method": "GET", "flow": "demo"}],
        flows=[{"name": "demo"}],
        models=[{"flow": "demo", "model": "gpt-4"}],
    )
    store.save_definitions(definitions, merge_existing=False)
    loaded = store.load_definitions()
    assert loaded.as_dict() == definitions.as_dict()
