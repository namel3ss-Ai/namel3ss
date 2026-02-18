from __future__ import annotations

from namel3ss.ingestion import extract as extract_mod


def test_extract_pages_pdf_prefers_pypdf_when_available(monkeypatch) -> None:
    monkeypatch.setattr(
        extract_mod,
        "_extract_pdf_pages_with_pypdf",
        lambda _content: ["Alpha page", "Beta page"],
    )

    def _legacy_parser(*_args, **_kwargs):
        raise AssertionError("legacy parser should not run when pypdf text exists")

    monkeypatch.setattr(extract_mod, "_extract_pdf_pages", _legacy_parser)

    pages, method = extract_mod.extract_pages(b"%PDF-1.4\n", detected={"type": "pdf"}, mode="primary")

    assert pages == ["Alpha page", "Beta page"]
    assert method == "primary"


def test_extract_pages_pdf_falls_back_when_pypdf_has_no_text(monkeypatch) -> None:
    monkeypatch.setattr(
        extract_mod,
        "_extract_pdf_pages_with_pypdf",
        lambda _content: ["", ""],
    )
    monkeypatch.setattr(
        extract_mod,
        "_extract_pdf_pages",
        lambda _content, *, layout: ["legacy parser page"],
    )

    pages, method = extract_mod.extract_pages(b"%PDF-1.4\n", detected={"type": "pdf"}, mode="primary")

    assert pages == ["legacy parser page"]
    assert method == "primary"


def test_extract_pages_fallback_prefers_pypdf_when_available(monkeypatch) -> None:
    monkeypatch.setattr(
        extract_mod,
        "_extract_pdf_pages_with_pypdf",
        lambda _content: ["Recovered text"],
    )

    def _legacy_parser(*_args, **_kwargs):
        raise AssertionError("legacy parser should not run when pypdf text exists")

    monkeypatch.setattr(extract_mod, "_extract_pdf_pages", _legacy_parser)

    pages, method = extract_mod.extract_pages_fallback(b"%PDF-1.4\n", detected={"type": "pdf"})

    assert pages == ["Recovered text"]
    assert method == "layout"


def test_extract_pages_ocr_prefers_ocr_backend(monkeypatch) -> None:
    monkeypatch.setattr(
        extract_mod,
        "_extract_pdf_pages_with_ocr",
        lambda _content: ["Scanned OCR page"],
    )

    def _legacy_parser(*_args, **_kwargs):
        raise AssertionError("legacy parser should not run when OCR page text exists")

    monkeypatch.setattr(extract_mod, "_extract_pdf_pages_with_pypdf", _legacy_parser)

    pages, method = extract_mod.extract_pages(b"%PDF-1.4\n", detected={"type": "pdf"}, mode="ocr")

    assert pages == ["Scanned OCR page"]
    assert method == "ocr"


def test_extract_pages_pdf_repairs_recoverable_mojibake(monkeypatch) -> None:
    monkeypatch.setattr(
        extract_mod,
        "_extract_pdf_pages_with_pypdf",
        lambda _content: ["Caf\u00c3\u00a9 policy summary"],
    )

    def _legacy_parser(*_args, **_kwargs):
        raise AssertionError("legacy parser should not run when repaired pypdf text is readable")

    monkeypatch.setattr(extract_mod, "_extract_pdf_pages", _legacy_parser)

    pages, method = extract_mod.extract_pages(b"%PDF-1.4\n", detected={"type": "pdf"}, mode="primary")

    assert pages == ["Caf\u00e9 policy summary"]
    assert method == "primary"


def test_extract_pages_pdf_falls_back_when_pypdf_text_is_unreadable(monkeypatch) -> None:
    monkeypatch.setattr(
        extract_mod,
        "_extract_pdf_pages_with_pypdf",
        lambda _content: ["\u00c3\u00c3\u00c3\u00c3\u00c3\u00c3\u00c3\u00c3"],
    )
    monkeypatch.setattr(
        extract_mod,
        "_extract_pdf_pages",
        lambda _content, *, layout: ["Recovered text page"],
    )

    pages, method = extract_mod.extract_pages(b"%PDF-1.4\n", detected={"type": "pdf"}, mode="primary")

    assert pages == ["Recovered text page"]
    assert method == "primary"
