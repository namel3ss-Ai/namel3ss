from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.datasets import add_dataset_version, dataset_history, load_dataset_registry
from namel3ss.errors.base import Namel3ssError


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app


def test_dataset_registry_add_list_history(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    path, first = add_dataset_version(
        project_root=tmp_path,
        app_path=app,
        dataset_name="faq-dataset",
        version="1.0.0",
        schema={"question": "text", "answer": "text"},
        source="faq_upload_1",
        transformations=["removed empty answers"],
        owner="ml-team",
    )
    assert path.exists()
    assert first.version == "1.0.0"

    _, second = add_dataset_version(
        project_root=tmp_path,
        app_path=app,
        dataset_name="faq-dataset",
        version="1.1.0",
        schema={"question": "text", "answer": "text"},
        source="faq_upload_2",
        transformations=["normalized whitespace"],
        owner="ml-team",
    )
    assert second.version == "1.1.0"

    registry = load_dataset_registry(tmp_path, app, required=True)
    assert len(registry.datasets) == 1
    history = dataset_history(project_root=tmp_path, app_path=app, dataset_name="faq-dataset")
    assert [entry.version for entry in history] == ["1.0.0", "1.1.0"]


def test_dataset_registry_rejects_duplicate_version(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    add_dataset_version(
        project_root=tmp_path,
        app_path=app,
        dataset_name="faq-dataset",
        version="1.0.0",
        schema={"question": "text"},
        source="faq_upload_1",
    )
    with pytest.raises(Namel3ssError):
        add_dataset_version(
            project_root=tmp_path,
            app_path=app,
            dataset_name="faq-dataset",
            version="1.0.0",
            schema={"question": "text"},
            source="faq_upload_2",
        )


def test_dataset_registry_normalizes_file_uri_source(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    path, entry = add_dataset_version(
        project_root=tmp_path,
        app_path=app,
        dataset_name="faq-dataset",
        version="1.0.0",
        schema={"question": "text"},
        source="file:///tmp/faq.csv",
    )
    assert path.exists()
    assert entry.source == "/tmp/faq.csv"


def test_dataset_registry_rejects_malformed_file_uri_source(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    with pytest.raises(Namel3ssError):
        add_dataset_version(
            project_root=tmp_path,
            app_path=app,
            dataset_name="faq-dataset",
            version="1.0.0",
            schema={"question": "text"},
            source="file:///tmp/faq.csv?bad=1",
        )
