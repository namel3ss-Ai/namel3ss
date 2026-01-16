from __future__ import annotations

from namel3ss.cli.main import main
from namel3ss.icons.registry import icon_names


def _collect(output: str) -> list[str]:
    return [line.strip()[2:] for line in output.splitlines() if line.strip().startswith("- ")]


def test_icons_command_lists_icons(capsys):
    code = main(["icons"])
    out = capsys.readouterr().out
    assert code == 0
    words = _collect(out)
    assert words == sorted(words)
    first_known = icon_names()[0]
    assert first_known in words


def test_icons_command_is_deterministic(capsys):
    code1 = main(["icons"])
    out1 = capsys.readouterr().out
    code2 = main(["icons"])
    out2 = capsys.readouterr().out
    assert code1 == 0 and code2 == 0
    assert out1 == out2
