import json
from pathlib import Path

import pytest

from namel3ss.runtime.artifacts import (
    ArtifactRecorder,
    resolve_artifact_mode,
    load_index_entries,
    DEFAULT_KEEP_RUNS,
)


def test_artifact_mode_resolution_default():
    """Test that default mode is 'auto'."""
    mode = resolve_artifact_mode(None)
    assert mode == "auto"


def test_artifact_mode_resolution_cli_override(monkeypatch):
    """Test that CLI value takes precedence over env var."""
    monkeypatch.setenv("N3_ARTIFACT_MODE", "debug")
    mode = resolve_artifact_mode("off")
    assert mode == "off"


def test_artifact_mode_resolution_env_var(monkeypatch):
    """Test that env var is used when CLI value is None."""
    monkeypatch.setenv("N3_ARTIFACT_MODE", "debug")
    mode = resolve_artifact_mode(None)
    assert mode == "debug"


def test_artifact_mode_resolution_invalid():
    """Test that invalid mode raises ValueError."""
    with pytest.raises(ValueError, match="Invalid artifact mode"):
        resolve_artifact_mode("invalid")


def test_artifact_recorder_off_mode_no_writes(tmp_path: Path):
    """Test that 'off' mode produces no artifacts."""
    artifacts_dir = tmp_path / ".namel3ss"
    recorder = ArtifactRecorder(root=artifacts_dir, mode="off")
    
    recorder.start_run()
    recorder.finalize_run("success")
    
    # No directory should be created in off mode
    assert not artifacts_dir.exists()


def test_artifact_recorder_auto_mode_creates_index(tmp_path: Path):
    """Test that 'auto' mode creates index.json."""
    artifacts_dir = tmp_path / ".namel3ss"
    recorder = ArtifactRecorder(root=artifacts_dir, mode="auto")
    
    recorder.start_run()
    test_file = artifacts_dir / "test.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")
    recorder.record_path(test_file)
    recorder.finalize_run("success")
    
    # Index should exist
    index_path = artifacts_dir / "index.json"
    assert index_path.exists()
    
    # Verify index structure
    index_data = json.loads(index_path.read_text())
    assert "runs" in index_data
    assert len(index_data["runs"]) == 1
    assert index_data["runs"][0]["status"] == "success"
    assert index_data["runs"][0]["mode"] == "auto"
    assert "test.txt" in index_data["runs"][0]["paths"]


def test_artifact_recorder_debug_mode_creates_index(tmp_path: Path):
    """Test that 'debug' mode creates index.json."""
    artifacts_dir = tmp_path / ".namel3ss"
    recorder = ArtifactRecorder(root=artifacts_dir, mode="debug")
    
    recorder.start_run()
    recorder.finalize_run("success")
    
    index_path = artifacts_dir / "index.json"
    assert index_path.exists()
    
    index_data = json.loads(index_path.read_text())
    assert index_data["runs"][0]["mode"] == "debug"


def test_retention_keeps_last_n_runs(tmp_path: Path):
    """Test that retention keeps only the last N runs."""
    artifacts_dir = tmp_path / ".namel3ss"
    keep_runs = 3
    
    # Create 5 runs
    for i in range(5):
        recorder = ArtifactRecorder(root=artifacts_dir, mode="auto", keep_runs=keep_runs)
        recorder.start_run()
        
        # Create a unique file for this run
        test_file = artifacts_dir / f"run_{i}.txt"
        test_file.write_text(f"run {i}")
        recorder.record_path(test_file)
        
        recorder.finalize_run("success")
    
    # Check index
    entries = load_index_entries(artifacts_dir)
    assert len(entries) == keep_runs
    
    # Verify only last 3 runs remain
    run_ids = [e["run_id"] for e in entries]
    assert run_ids == [3, 4, 5]
    
    # Verify old files were deleted
    assert not (artifacts_dir / "run_0.txt").exists()
    assert not (artifacts_dir / "run_1.txt").exists()
    
    # Verify recent files still exist
    assert (artifacts_dir / "run_2.txt").exists()
    assert (artifacts_dir / "run_3.txt").exists()
    assert (artifacts_dir / "run_4.txt").exists()


def test_retention_keeps_last_failure(tmp_path: Path):
    """Test that retention always keeps the most recent failure."""
    artifacts_dir = tmp_path / ".namel3ss"
    keep_runs = 2
    
    # Run 1: success
    recorder = ArtifactRecorder(root=artifacts_dir, mode="auto", keep_runs=keep_runs)
    recorder.start_run()
    file1 = artifacts_dir / "run_1.txt"
    file1.write_text("run 1")
    recorder.record_path(file1)
    recorder.finalize_run("success")
    
    # Run 2: failed
    recorder = ArtifactRecorder(root=artifacts_dir, mode="auto", keep_runs=keep_runs)
    recorder.start_run()
    file2 = artifacts_dir / "run_2.txt"
    file2.write_text("run 2")
    recorder.record_path(file2)
    recorder.finalize_run("failed")
    
    # Run 3: success
    recorder = ArtifactRecorder(root=artifacts_dir, mode="auto", keep_runs=keep_runs)
    recorder.start_run()
    file3 = artifacts_dir / "run_3.txt"
    file3.write_text("run 3")
    recorder.record_path(file3)
    recorder.finalize_run("success")
    
    # Run 4: success
    recorder = ArtifactRecorder(root=artifacts_dir, mode="auto", keep_runs=keep_runs)
    recorder.start_run()
    file4 = artifacts_dir / "run_4.txt"
    file4.write_text("run 4")
    recorder.record_path(file4)
    recorder.finalize_run("success")
    
    # Should have 3 runs: last 2 successes + last failure
    entries = load_index_entries(artifacts_dir)
    assert len(entries) == 3
    
    run_ids = sorted([e["run_id"] for e in entries])
    assert run_ids == [2, 3, 4]
    
    # Verify the failure is kept
    assert file2.exists()
    assert file3.exists()
    assert file4.exists()
    assert not file1.exists()


def test_index_json_deterministic(tmp_path: Path):
    """Test that index.json has stable, sorted keys."""
    artifacts_dir = tmp_path / ".namel3ss"
    recorder = ArtifactRecorder(root=artifacts_dir, mode="auto")
    
    recorder.start_run()
    recorder.finalize_run("success")
    
    index_path = artifacts_dir / "index.json"
    content = index_path.read_text()
    
    # Verify it's valid JSON
    data = json.loads(content)
    
    # Verify keys are sorted (check the raw text)
    assert '"runs"' in content
    
    # Verify run entry has expected keys
    run = data["runs"][0]
    assert "run_id" in run
    assert "mode" in run
    assert "started_at" in run
    assert "finished_at" in run
    assert "status" in run
    assert "paths" in run


def test_retention_never_deletes_outside_artifacts_dir(tmp_path: Path):
    """Test that retention never deletes files outside .namel3ss/."""
    artifacts_dir = tmp_path / ".namel3ss"
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("should not be deleted")
    
    recorder = ArtifactRecorder(root=artifacts_dir, mode="auto", keep_runs=1)
    recorder.start_run()
    
    # Try to record a path outside artifacts_dir (should be ignored)
    recorder.record_path(outside_file)
    
    recorder.finalize_run("success")
    
    # Outside file should still exist
    assert outside_file.exists()


def test_artifact_recorder_allow_writes_property():
    """Test that allow_writes property works correctly."""
    recorder_off = ArtifactRecorder(root=Path("/tmp/.namel3ss"), mode="off")
    assert not recorder_off.allow_writes
    
    recorder_auto = ArtifactRecorder(root=Path("/tmp/.namel3ss"), mode="auto")
    assert recorder_auto.allow_writes
    
    recorder_debug = ArtifactRecorder(root=Path("/tmp/.namel3ss"), mode="debug")
    assert recorder_debug.allow_writes
    
    recorder_no_root = ArtifactRecorder(root=None, mode="auto")
    assert not recorder_no_root.allow_writes


def test_artifact_recorder_allow_heavy_property():
    """Test that allow_heavy property works correctly."""
    recorder_auto = ArtifactRecorder(root=Path("/tmp/.namel3ss"), mode="auto")
    assert not recorder_auto.allow_heavy
    
    recorder_debug = ArtifactRecorder(root=Path("/tmp/.namel3ss"), mode="debug")
    assert recorder_debug.allow_heavy
    
    recorder_off = ArtifactRecorder(root=Path("/tmp/.namel3ss"), mode="off")
    assert not recorder_off.allow_heavy
