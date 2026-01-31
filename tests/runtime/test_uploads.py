from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.backend.upload_handler import handle_upload, handle_upload_list
from namel3ss.runtime.backend.upload_store import normalize_hash_bytes, store_upload
from namel3ss.utils.slugify import slugify_text


def _ctx(tmp_path: Path, *, capabilities: tuple[str, ...] = ("uploads",)) -> SimpleNamespace:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return SimpleNamespace(
        capabilities=capabilities,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def _chunked_body(chunks: list[bytes]) -> bytes:
    parts: list[bytes] = []
    for chunk in chunks:
        parts.append(f"{len(chunk):X}\r\n".encode("ascii"))
        parts.append(chunk)
        parts.append(b"\r\n")
    parts.append(b"0\r\n\r\n")
    return b"".join(parts)


def test_store_upload_scoped_and_indexed(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    payload = b"hello world"
    metadata = store_upload(
        ctx,
        filename="report.txt",
        content_type="text/plain",
        stream=io.BytesIO(payload),
    )
    checksum = hashlib.sha256(payload).hexdigest()
    scope = slugify_text("app.ai")
    expected_name = f"report-{checksum[:12]}.txt"
    expected_path = f"{scope}/uploads/{expected_name}"

    assert metadata["bytes"] == len(payload)
    assert metadata["checksum"] == checksum
    assert metadata["stored_path"] == expected_path
    assert str(tmp_path) not in metadata["stored_path"]
    preview = metadata.get("preview", {})
    assert preview.get("filename") == "report.txt"
    assert preview.get("content_type") == "text/plain"
    assert preview.get("size") == len(payload)
    assert preview.get("checksum") == checksum
    assert preview.get("item_count") == 1

    target = tmp_path / ".namel3ss" / "files" / scope / "uploads" / expected_name
    assert target.exists()

    index_path = target.parent / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index
    assert index[0]["stored_path"] == expected_path


def test_upload_checksum_normalizes_newlines(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    payload_lf = b"policy line\nnext line\n"
    payload_crlf = b"policy line\r\nnext line\r\n"
    meta_lf = store_upload(ctx, filename="policy_lf.txt", content_type="text/plain", stream=io.BytesIO(payload_lf))
    meta_crlf = store_upload(ctx, filename="policy_crlf.txt", content_type="text/plain", stream=io.BytesIO(payload_crlf))
    expected = hashlib.sha256(normalize_hash_bytes(payload_lf)).hexdigest()
    assert meta_lf["checksum"] == expected
    assert meta_crlf["checksum"] == expected


def test_handle_upload_multipart(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    boundary = "n3-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="hello.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "hello world\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    response = handle_upload(
        ctx,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        rfile=io.BytesIO(body),
        content_length=len(body),
        upload_name=None,
    )
    upload = response["upload"]
    checksum = hashlib.sha256(b"hello world").hexdigest()

    assert response["ok"] is True
    assert upload["name"] == "hello.txt"
    assert upload["content_type"] == "text/plain"
    assert upload["bytes"] == 11
    assert upload["checksum"] == checksum
    assert str(tmp_path) not in upload["stored_path"]
    assert upload["state"] == "stored"
    assert upload["progress"]["percent_complete"] == 100
    assert upload["preview"]["filename"] == "hello.txt"

    traces = response["traces"]
    assert [trace["type"] for trace in traces] == [
        "upload_state",
        "upload_state",
        "upload_progress",
        "upload_state",
        "upload_preview",
        "upload_received",
        "upload_stored",
        "upload_state",
    ]


def test_handle_upload_chunked(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    payload = b"chunked data"
    body = _chunked_body([b"chunked ", b"data"])
    response = handle_upload(
        ctx,
        headers={"Content-Type": "application/octet-stream", "Transfer-Encoding": "chunked"},
        rfile=io.BytesIO(body),
        content_length=None,
        upload_name="chunked.bin",
    )
    upload = response["upload"]
    checksum = hashlib.sha256(payload).hexdigest()

    assert upload["name"] == "chunked.bin"
    assert upload["bytes"] == len(payload)
    assert upload["checksum"] == checksum
    assert upload["state"] == "stored"
    assert upload["progress"]["percent_complete"] == 100


def test_upload_list_is_sorted_and_scoped(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    store_upload(ctx, filename="zeta.txt", content_type="text/plain", stream=io.BytesIO(b"z"))
    store_upload(ctx, filename="alpha.txt", content_type="text/plain", stream=io.BytesIO(b"a"))
    response = handle_upload_list(ctx)
    assert response["ok"] is True
    stored_paths = [item.get("stored_path", "") for item in response["uploads"]]
    assert stored_paths == sorted(stored_paths)
    assert all(str(tmp_path) not in path for path in stored_paths)


def test_uploads_require_capability(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, capabilities=())
    with pytest.raises(Namel3ssError, match="Uploads capability is not enabled"):
        handle_upload(
            ctx,
            headers={"Content-Type": "application/octet-stream"},
            rfile=io.BytesIO(b"data"),
            content_length=4,
            upload_name="file.bin",
        )
    with pytest.raises(Namel3ssError, match="Uploads capability is not enabled"):
        handle_upload_list(ctx)
