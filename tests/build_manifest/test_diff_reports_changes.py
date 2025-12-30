from namel3ss.runtime.build.explain.diff import diff_manifests
from namel3ss.runtime.build.explain.manifest import BuildManifest


def test_diff_reports_changes() -> None:
    old = BuildManifest(
        api_version="build.v1",
        build_id="old",
        created_at="2024-01-01T00:00:00+00:00",
        project_root="/tmp/project",
        app_path="/tmp/project/app.ai",
        inputs={"files": [{"path": "app.ai", "sha256": "aaa"}], "source_fingerprint": "one", "config": {}},
        guarantees=["execution explanations recorded (how)"],
        constraints=[],
        capabilities={},
        components={},
        changes=None,
        notes=[],
    )
    new = BuildManifest(
        api_version="build.v1",
        build_id="new",
        created_at="2024-01-02T00:00:00+00:00",
        project_root="/tmp/project",
        app_path="/tmp/project/app.ai",
        inputs={"files": [{"path": "app.ai", "sha256": "bbb"}], "source_fingerprint": "two", "config": {}},
        guarantees=["execution explanations recorded (how)", "tool decisions recorded (with)"],
        constraints=[],
        capabilities={},
        components={},
        changes=None,
        notes=[],
    )
    diff = diff_manifests(old, new)
    assert diff.get("files_changed_count") == 1
    assert "app.ai" in diff.get("files_changed", [])
    assert "tool decisions recorded (with)" in diff.get("guarantees_added", [])
