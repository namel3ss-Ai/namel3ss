from pathlib import Path

from namel3ss.cli.main import main


def _write_minimal_app(root: Path) -> None:
    (root / "app.ai").write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")


def test_run_artifacts_flag_defaults_to_auto(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test that default run has artifact mode 'auto' (creates artifacts)."""
    _write_minimal_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    
    code = main(["run", "--target", "local"])
    
    out = capsys.readouterr().out
    assert code == 0
    assert (tmp_path / ".namel3ss").exists()
    assert (tmp_path / ".namel3ss" / "index.json").exists()


def test_run_artifacts_off_flag(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test that --artifacts off prevents artifact creation."""
    _write_minimal_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    
    code = main(["run", "--target", "local", "--artifacts", "off"])
    
    out = capsys.readouterr().out
    assert code == 0
    assert not (tmp_path / ".namel3ss").exists()


def test_run_artifacts_debug_flag(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test that --artifacts debug works."""
    _write_minimal_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    
    code = main(["run", "--target", "local", "--artifacts", "debug"])
    
    out = capsys.readouterr().out
    assert code == 0
    assert (tmp_path / ".namel3ss").exists()
    assert (tmp_path / ".namel3ss" / "index.json").read_text().find('"mode": "debug"') != -1


def test_run_artifacts_env_var(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test that N3_ARTIFACT_MODE env var works."""
    _write_minimal_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("N3_ARTIFACT_MODE", "off")
    
    code = main(["run", "--target", "local"])
    
    out = capsys.readouterr().out
    assert code == 0
    assert not (tmp_path / ".namel3ss").exists()


def test_run_artifacts_flag_precedence(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test that CLI flag overrides env var."""
    _write_minimal_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("N3_ARTIFACT_MODE", "off")
    
    # Env says off, CLI says debug -> should be debug
    code = main(["run", "--target", "local", "--artifacts", "debug"])
    
    out = capsys.readouterr().out
    assert code == 0
    assert (tmp_path / ".namel3ss").exists()
    assert (tmp_path / ".namel3ss" / "index.json").read_text().find('"mode": "debug"') != -1
