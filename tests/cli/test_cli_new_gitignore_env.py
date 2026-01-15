from namel3ss.cli.main import main


def test_new_creates_gitignore_with_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = main(["new", "starter", "demo_app"])
    assert code == 0
    gitignore = tmp_path / "demo_app" / ".gitignore"
    assert gitignore.exists()
    assert ".env" in gitignore.read_text(encoding="utf-8")
