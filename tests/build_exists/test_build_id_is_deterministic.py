from pathlib import Path

from namel3ss.runtime.build.explain.collect import collect_inputs
from namel3ss.runtime.build.explain.fingerprint import compute_build_id
from namel3ss.runtime.build.explain.guarantees import infer_guarantees


def _write_app(tmp_path: Path, content: str) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(content, encoding="utf-8")
    return app_path


def test_build_id_is_deterministic(tmp_path: Path) -> None:
    app_path = _write_app(
        tmp_path,
        """
spec is "1.0"

flow "demo":
  return "ok"
""".lstrip(),
    )
    inputs = collect_inputs(tmp_path, app_path)
    guarantees, constraints, capabilities, _components = infer_guarantees(tmp_path)
    build_id_one = compute_build_id(
        api_version="build.v1",
        source_fingerprint=inputs.get("source_fingerprint") or "",
        guarantees=guarantees,
        constraints=constraints,
        capabilities=capabilities,
    )
    build_id_two = compute_build_id(
        api_version="build.v1",
        source_fingerprint=inputs.get("source_fingerprint") or "",
        guarantees=guarantees,
        constraints=constraints,
        capabilities=capabilities,
    )
    assert build_id_one == build_id_two
