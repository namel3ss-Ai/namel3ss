from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.ingestion.chunk_plan import plan_chunks, plan_to_payload
from namel3ss.ingestion.hash import hash_text
from namel3ss.ingestion.normalize import normalize_text
from namel3ss.lexer.lexer import Lexer
from namel3ss.lexer.scan_payload import tokens_to_payload
from namel3ss.runtime.native import (
    NativeStatus,
    native_available,
    native_chunk_plan,
    native_hash,
    native_normalize,
    native_scan,
)
from namel3ss.runtime.native import loader as native_loader

FIXTURES = Path("tests/fixtures/native")


@pytest.fixture(autouse=True)
def _reset_native_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("N3_NATIVE", raising=False)
    monkeypatch.delenv("N3_NATIVE_LIB", raising=False)
    native_loader._reset_native_state()


def test_scan_payload_matches_golden() -> None:
    source = (FIXTURES / "scan_basic.ai").read_text(encoding="utf-8")
    expected = (FIXTURES / "scan_basic.json").read_bytes()
    tokens = Lexer(source)._tokenize_python()
    payload = tokens_to_payload(tokens)
    assert payload == expected


def test_normalize_matches_golden() -> None:
    raw = (FIXTURES / "text_sample.txt").read_text(encoding="utf-8")
    expected = (FIXTURES / "text_sample.normalized.txt").read_text(encoding="utf-8")
    assert normalize_text(raw) == expected


def test_hash_matches_golden() -> None:
    raw = (FIXTURES / "text_sample.txt").read_text(encoding="utf-8")
    expected = (FIXTURES / "text_sample.sha256.txt").read_text(encoding="utf-8")
    assert hash_text(raw) == expected


def test_chunk_plan_matches_golden() -> None:
    text = (FIXTURES / "text_sample.normalized.txt").read_text(encoding="utf-8")
    expected = (FIXTURES / "text_sample.chunk_plan.json").read_bytes()
    payload = plan_to_payload(plan_chunks(text, max_chars=40, overlap=5))
    assert payload == expected


def test_native_scan_matches_golden(monkeypatch: pytest.MonkeyPatch) -> None:
    _require_native(monkeypatch)
    source = (FIXTURES / "scan_basic.ai").read_text(encoding="utf-8").encode("utf-8")
    expected = (FIXTURES / "scan_basic.json").read_bytes()
    first = native_scan(source)
    second = native_scan(source)
    assert first.status == NativeStatus.OK
    assert first.payload == expected
    assert second.payload == expected


def test_native_normalize_matches_golden(monkeypatch: pytest.MonkeyPatch) -> None:
    _require_native(monkeypatch)
    raw = (FIXTURES / "text_sample.txt").read_text(encoding="utf-8").encode("utf-8")
    expected = (FIXTURES / "text_sample.normalized.txt").read_bytes()
    first = native_normalize(raw)
    second = native_normalize(raw)
    assert first.status == NativeStatus.OK
    assert first.payload == expected
    assert second.payload == expected


def test_native_hash_matches_golden(monkeypatch: pytest.MonkeyPatch) -> None:
    _require_native(monkeypatch)
    raw = (FIXTURES / "text_sample.txt").read_text(encoding="utf-8").encode("utf-8")
    expected = (FIXTURES / "text_sample.sha256.txt").read_bytes()
    first = native_hash(raw)
    second = native_hash(raw)
    assert first.status == NativeStatus.OK
    assert first.payload == expected
    assert second.payload == expected


def test_native_chunk_plan_matches_golden(monkeypatch: pytest.MonkeyPatch) -> None:
    _require_native(monkeypatch)
    text = (FIXTURES / "text_sample.normalized.txt").read_text(encoding="utf-8").encode("utf-8")
    expected = (FIXTURES / "text_sample.chunk_plan.json").read_bytes()
    first = native_chunk_plan(text, max_chars=40, overlap=5)
    second = native_chunk_plan(text, max_chars=40, overlap=5)
    assert first.status == NativeStatus.OK
    assert first.payload == expected
    assert second.payload == expected


def _require_native(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("N3_NATIVE", "1")
    native_loader._reset_native_state()
    if not native_available():
        pytest.skip("native library not available")
