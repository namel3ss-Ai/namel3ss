from pathlib import Path

from tools.clean_pattern_artifacts import clean_pattern_artifacts


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_cleans_runtime_artifacts_but_keeps_tools_yaml(tmp_path: Path) -> None:
    repo_root = tmp_path
    tools_path = repo_root / "patterns/demo/.namel3ss/tools.yaml"
    artifact_path = repo_root / "patterns/demo/.namel3ss/execution/last.json"
    _write(tools_path, "tools: []")
    _write(artifact_path, '{"ok":true}')

    removed = clean_pattern_artifacts(repo_root)

    assert not list(repo_root.glob("patterns/**/.namel3ss/execution/last.json"))
    assert not artifact_path.exists()
    assert tools_path.exists()
    assert repo_root.joinpath("patterns/demo/.namel3ss").is_dir()
    assert artifact_path.parent in removed


def test_removes_artifacts_when_no_tools_file_present(tmp_path: Path) -> None:
    repo_root = tmp_path
    artifact_path = repo_root / "patterns/agents/example/.namel3ss/spec/last.json"
    _write(artifact_path, '{"status":"ok"}')

    removed = clean_pattern_artifacts(repo_root)

    assert repo_root.joinpath("patterns/agents/example/.namel3ss") in removed
    assert not repo_root.joinpath("patterns/agents/example/.namel3ss").exists()
