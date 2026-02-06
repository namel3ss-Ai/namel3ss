from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


@dataclass(frozen=True)
class DatasetSnapshot:
    path: str
    content_hash: str
    row_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "content_hash": self.content_hash,
            "row_count": self.row_count,
        }


@dataclass(frozen=True)
class DatasetPartition:
    snapshot: DatasetSnapshot
    rows: tuple[dict[str, object], ...]
    train_rows: tuple[dict[str, object], ...]
    validation_rows: tuple[dict[str, object], ...]


def load_jsonl_dataset(path: Path) -> tuple[dict[str, object], ...]:
    if not path.exists() or not path.is_file():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Dataset file not found: {path}",
                why="The training dataset path does not exist.",
                fix="Pass an existing JSONL file.",
                example="--dataset data/support_tickets.jsonl",
            )
        )
    rows: list[dict[str, object]] = []
    for index, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception as err:
            raise Namel3ssError(_invalid_dataset_line_message(path, index, "not valid JSON")) from err
        if not isinstance(payload, dict):
            raise Namel3ssError(_invalid_dataset_line_message(path, index, "row must be a JSON object"))
        rows.append(_normalize_row(payload))
    if not rows:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Dataset is empty: {path}",
                why="At least one training example is required.",
                fix="Add JSON object rows to the JSONL file.",
                example='{"input":"hello","target":"world"}',
            )
        )
    return tuple(rows)


def snapshot_dataset(path: Path, rows: tuple[dict[str, object], ...]) -> DatasetSnapshot:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return DatasetSnapshot(path=path.as_posix(), content_hash=digest, row_count=len(rows))


def partition_dataset(
    *,
    path: Path,
    rows: tuple[dict[str, object], ...],
    seed: int,
    validation_split: float,
) -> DatasetPartition:
    snapshot = snapshot_dataset(path, rows)
    keyed: list[tuple[str, dict[str, object]]] = []
    for index, row in enumerate(rows):
        canonical = canonical_json_dumps(row, pretty=False, drop_run_keys=False)
        digest = hashlib.sha256(f"{seed}:{index}:{canonical}".encode("utf-8")).hexdigest()
        keyed.append((digest, row))
    keyed.sort(key=lambda item: item[0])

    ordered_rows = tuple(item[1] for item in keyed)
    row_count = len(ordered_rows)
    validation_count = int(round(row_count * validation_split))
    validation_count = max(1, min(validation_count, row_count - 1)) if row_count > 1 else 1
    split_at = row_count - validation_count

    train_rows = ordered_rows[:split_at]
    validation_rows = ordered_rows[split_at:]
    if not train_rows:
        train_rows = ordered_rows[:-1]
        validation_rows = ordered_rows[-1:]

    return DatasetPartition(
        snapshot=snapshot,
        rows=ordered_rows,
        train_rows=tuple(train_rows),
        validation_rows=tuple(validation_rows),
    )


def convert_state_records_to_jsonl(records: Iterable[dict[str, object]], output_path: Path) -> dict[str, object]:
    normalized_rows: list[dict[str, object]] = []
    for item in records:
        if not isinstance(item, dict):
            raise Namel3ssError(
                build_guidance_message(
                    what="State record conversion failed.",
                    why="Each state record must be a JSON object.",
                    fix="Provide a list of object records.",
                    example='[{"input":"question","target":"answer"}]',
                )
            )
        normalized_rows.append(_normalize_row(item))

    if not normalized_rows:
        raise Namel3ssError(
            build_guidance_message(
                what="State record conversion failed.",
                why="The input list is empty.",
                fix="Provide at least one record.",
                example='[{"input":"question","target":"answer"}]',
            )
        )

    ordered = sorted(
        normalized_rows,
        key=lambda row: hashlib.sha256(canonical_json_dumps(row, pretty=False, drop_run_keys=False).encode("utf-8")).hexdigest(),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [canonical_json_dumps(row, pretty=False, drop_run_keys=False) for row in ordered]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "rows": len(ordered),
        "output": output_path.as_posix(),
    }


def _normalize_row(payload: dict[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key in sorted(payload.keys(), key=lambda item: str(item)):
        normalized[str(key)] = _normalize_scalar(payload[key])
    if "input" not in normalized:
        # Keep dataset contracts explicit for training/evaluation.
        normalized["input"] = ""
    return normalized


def _normalize_scalar(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_normalize_scalar(item) for item in value]
    if isinstance(value, dict):
        nested: dict[str, object] = {}
        for key in sorted(value.keys(), key=lambda item: str(item)):
            nested[str(key)] = _normalize_scalar(value[key])
        return nested
    return str(value)


def _invalid_dataset_line_message(path: Path, line_no: int, details: str) -> str:
    return build_guidance_message(
        what=f"Dataset parse failed at {path}:{line_no}",
        why=details,
        fix="Use JSONL with one JSON object per line.",
        example='{"input":"hello","target":"world"}',
    )


__all__ = [
    "DatasetPartition",
    "DatasetSnapshot",
    "convert_state_records_to_jsonl",
    "load_jsonl_dataset",
    "partition_dataset",
    "snapshot_dataset",
]
