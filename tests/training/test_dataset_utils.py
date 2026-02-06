from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.training import convert_state_records_to_jsonl, load_jsonl_dataset, partition_dataset


def _write_dataset(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_convert_state_records_to_jsonl_is_deterministic(tmp_path: Path) -> None:
    rows = [
        {"target": "A", "input": "Q1"},
        {"input": "Q2", "target": "B", "extra": {"z": 1, "a": 2}},
    ]
    out_path = tmp_path / "out" / "dataset.jsonl"

    first = convert_state_records_to_jsonl(rows, out_path)
    first_text = out_path.read_text(encoding="utf-8")

    second = convert_state_records_to_jsonl(rows, out_path)
    second_text = out_path.read_text(encoding="utf-8")

    assert first == second
    assert first_text == second_text
    assert first["rows"] == 2


def test_load_and_partition_dataset_are_deterministic(tmp_path: Path) -> None:
    dataset = _write_dataset(
        tmp_path / "data" / "train.jsonl",
        [
            {"input": "q1", "target": "a1"},
            {"input": "q2", "target": "a2"},
            {"input": "q3", "target": "a3"},
            {"input": "q4", "target": "a4"},
        ],
    )

    rows = load_jsonl_dataset(dataset)
    first = partition_dataset(path=dataset, rows=rows, seed=19, validation_split=0.25)
    second = partition_dataset(path=dataset, rows=rows, seed=19, validation_split=0.25)

    assert first.snapshot.content_hash == second.snapshot.content_hash
    assert first.train_rows == second.train_rows
    assert first.validation_rows == second.validation_rows


def test_load_jsonl_dataset_rejects_invalid_row(tmp_path: Path) -> None:
    dataset = tmp_path / "data" / "bad.jsonl"
    dataset.parent.mkdir(parents=True, exist_ok=True)
    dataset.write_text('{"input":"ok"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(Namel3ssError, match="Dataset parse failed"):
        load_jsonl_dataset(dataset)


def test_convert_state_records_rejects_empty_input(tmp_path: Path) -> None:
    with pytest.raises(Namel3ssError, match="input list is empty"):
        convert_state_records_to_jsonl([], tmp_path / "out.jsonl")
