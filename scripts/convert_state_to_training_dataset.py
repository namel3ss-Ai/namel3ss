#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from namel3ss.errors.base import Namel3ssError
from namel3ss.training import convert_state_records_to_jsonl


class ConversionFailure(RuntimeError):
    """Raised when dataset conversion cannot complete."""


def convert_state_file(*, input_path: Path, output_path: Path) -> dict[str, object]:
    records = _load_records(input_path)
    try:
        return convert_state_records_to_jsonl(records, output_path)
    except Namel3ssError as err:
        raise ConversionFailure(str(err)) from err


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert state JSON records to deterministic JSONL training dataset.")
    parser.add_argument("--input", required=True, help="Input JSON file (list of records or {records:[...]})")
    parser.add_argument("--output", required=True, help="Output JSONL file path")
    parser.add_argument("--check", action="store_true", help="Check conversion output matches existing --output")
    args = parser.parse_args(argv)

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    conversion_output = output_path
    if args.check:
        conversion_output = (output_path.parent / f".{output_path.name}.tmp").resolve()

    try:
        payload = convert_state_file(input_path=input_path, output_path=conversion_output)
    except ConversionFailure as err:
        print(f"Dataset conversion failed: {err}", file=sys.stderr)
        return 1

    if args.check:
        expected = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        generated = Path(payload["output"]).read_text(encoding="utf-8")
        try:
            conversion_output.unlink(missing_ok=True)
        except Exception:
            pass
        if expected != generated:
            print("Dataset conversion check failed: output differs from expected file.", file=sys.stderr)
            return 1
        print(f"Dataset conversion check passed: {output_path}")
        return 0

    print(f"Training dataset written: {output_path} ({payload['rows']} rows)")
    return 0


def _load_records(path: Path) -> list[dict[str, object]]:
    if not path.exists() or not path.is_file():
        raise ConversionFailure(f"Input file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise ConversionFailure(f"Input file is not valid JSON: {path}") from err
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        rows = payload.get("records", payload.get("rows"))
        if isinstance(rows, list):
            return [item for item in rows if isinstance(item, dict)]
    raise ConversionFailure("Input JSON must be a list of records or an object with records/rows list.")


if __name__ == "__main__":
    raise SystemExit(main())
