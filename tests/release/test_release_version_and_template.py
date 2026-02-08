from importlib import metadata
from pathlib import Path
import re

from namel3ss.cli.main import main
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.version import get_version


def _pyproject_version(pyproject_text: str) -> str:
    match = re.search(r'^\s*version\s*=\s*"([^"]+)"', pyproject_text, flags=re.MULTILINE)
    return match.group(1) if match else ""


def test_release_version_and_template(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[2]
    version_path = root / "VERSION"
    pyproject_path = root / "pyproject.toml"

    version_text = version_path.read_text(encoding="utf-8").strip()
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    assert version_text
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[abrc]\d+)?", version_text)
    assert _pyproject_version(pyproject_text) == version_text
    def _raise(_name: str) -> str:
        raise metadata.PackageNotFoundError
    monkeypatch.setattr("namel3ss.version.metadata.version", _raise)
    assert get_version() == version_text

    monkeypatch.chdir(tmp_path)
    code = main(["new", "operations_dashboard", "test_app"])
    assert code == 0

    app_path = tmp_path / "test_app" / "app.ai"
    source = app_path.read_text(encoding="utf-8")
    ast_program = parse(source)
    lower_program(ast_program)
