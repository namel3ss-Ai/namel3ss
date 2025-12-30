import json
from pathlib import Path

from namel3ss.runtime.flow.explain.builder import build_flow_explain_pack
from namel3ss.runtime.flow.explain.render_plain import render_what

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _write_fixture(root: Path, subdir: str, payload: dict) -> None:
    target = root / ".namel3ss" / subdir / "last.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _prepare_root(tmp_path: Path) -> Path:
    _write_fixture(tmp_path, "run", _load_fixture("run_last.json"))
    _write_fixture(tmp_path, "execution", _load_fixture("execution_last.json"))
    _write_fixture(tmp_path, "tools", _load_fixture("tools_last.json"))
    _write_fixture(tmp_path, "memory", _load_fixture("memory_last.json"))
    return tmp_path


def test_render_is_deterministic(tmp_path: Path) -> None:
    root = _prepare_root(tmp_path)
    pack = build_flow_explain_pack(root, None)
    assert pack is not None
    text_one = render_what(pack)
    text_two = render_what(pack)
    assert text_one == text_two
