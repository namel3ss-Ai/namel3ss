from namel3ss.ui.external.detect import detect_external_ui, resolve_external_ui_root


def test_external_ui_detection_false_without_ui(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n', encoding="utf-8")
    assert detect_external_ui(tmp_path, app_path) is False
    assert resolve_external_ui_root(tmp_path, app_path) is None


def test_external_ui_detection_true_with_ui(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n', encoding="utf-8")
    ui_root = tmp_path / "ui"
    ui_root.mkdir()
    assert detect_external_ui(tmp_path, app_path) is True
    assert resolve_external_ui_root(tmp_path, app_path) == ui_root.resolve()
