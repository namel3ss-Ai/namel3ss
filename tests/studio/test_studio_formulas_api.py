import json
from pathlib import Path

from namel3ss.studio.formulas_api import get_formulas_payload


SOURCE = '''spec is "1.0"

flow "demo":
  let numbers is list:
    1
    2
  calc:
    doubled = map numbers with item as n:
      n * 2
    state.total = reduce doubled with acc as s and item as v starting 0:
      s + v
    avg = mean(doubled)
'''


def test_formulas_payload_extracts_calc_blocks() -> None:
    payload = get_formulas_payload(SOURCE)
    assert payload["ok"] is True
    blocks = payload["blocks"]
    assert len(blocks) == 1
    block = blocks[0]
    assert block["flow"] == "demo"
    assignments = block["assignments"]
    assert len(assignments) == 3

    first = assignments[0]
    assert first["line_start"] == 8
    assert first["line_end"] == 9
    assert first["lhs"] == "doubled"
    assert first["rhs"].startswith("map numbers")
    assert first["body"] == ["n * 2"]
    assert first["code"] == "    doubled = map numbers with item as n:\n      n * 2"

    second = assignments[1]
    assert second["line_start"] == 10
    assert second["line_end"] == 11
    assert second["lhs"] == "state.total"
    assert "reduce doubled" in second["rhs"]

    third = assignments[2]
    assert third["line_start"] == 12
    assert third["line_end"] == 12
    assert third["rhs"].startswith("mean")


def test_formulas_payload_golden() -> None:
    payload = get_formulas_payload(SOURCE)
    assert payload["ok"] is True
    actual = _canonical_json(payload)
    expected = Path("tests/fixtures/formulas_payload_golden.json").read_text(encoding="utf-8")
    assert actual == expected


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
