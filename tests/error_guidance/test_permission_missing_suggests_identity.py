import json
from pathlib import Path

from namel3ss.runtime.errors.explain.builder import build_error_explain_pack

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _write_fixture(root: Path, subdir: str, payload: dict) -> None:
    target = root / ".namel3ss" / subdir / "last.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_permission_missing_suggests_identity(tmp_path: Path) -> None:
    _write_fixture(tmp_path, "run", _load_fixture("run_last_permission.json"))
    pack = build_error_explain_pack(tmp_path)
    assert pack is not None
    error = pack.get("error") or {}
    options = error.get("recovery_options") or []
    option_ids = [entry.get("id") for entry in options if isinstance(entry, dict)]
    assert "provide_identity" in option_ids
