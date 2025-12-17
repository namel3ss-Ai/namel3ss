from pathlib import Path
import os

from namel3ss.config.dotenv import apply_dotenv, load_dotenv_for_path


def test_load_dotenv_parses_values(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        """# comment\nKEY=value\nQUOTED=\"hello world\"\nEQUALS=a=b=c\nBLANK=\nSPACED = spaced \n'ignored'\n""",
        encoding="utf-8",
    )
    values = load_dotenv_for_path(str(tmp_path / "app.ai"))
    assert values["KEY"] == "value"
    assert values["QUOTED"] == "hello world"
    assert values["EQUALS"] == "a=b=c"
    assert values["BLANK"] == ""
    assert values["SPACED"] == "spaced"


def test_apply_dotenv_respects_existing_env(monkeypatch):
    monkeypatch.setenv("KEY", "existing")
    apply_dotenv({"KEY": "new", "NEW": "val"})
    assert os.environ["KEY"] == "existing"
    assert os.environ["NEW"] == "val"
