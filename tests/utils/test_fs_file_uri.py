from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.utils.fs import resolve_file_uri


def test_resolve_file_uri_plain_path() -> None:
    value = "registry_ops.json"
    resolved = resolve_file_uri(value)
    assert resolved == Path("registry_ops.json")


def test_resolve_file_uri_unix_style_file_uri() -> None:
    resolved = resolve_file_uri("file:///tmp/registry_ops.json")
    assert resolved.as_posix() == "/tmp/registry_ops.json"


def test_resolve_file_uri_windows_drive_uri_with_leading_slash() -> None:
    resolved = resolve_file_uri("file:///C:/Users/demo/registry_ops.json")
    assert resolved.as_posix() == "C:/Users/demo/registry_ops.json"


def test_resolve_file_uri_windows_drive_uri_with_netloc() -> None:
    resolved = resolve_file_uri("file://C:/Users/demo/registry_ops.json")
    assert resolved.as_posix() == "C:/Users/demo/registry_ops.json"


def test_resolve_file_uri_rejects_malformed_query() -> None:
    with pytest.raises(ValueError):
        resolve_file_uri("file:///tmp/registry_ops.json?x=1")

