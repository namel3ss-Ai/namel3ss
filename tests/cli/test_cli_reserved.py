from __future__ import annotations

from namel3ss.cli.main import main


def _collect_words(output: str) -> list[str]:
    return [line.strip()[2:] for line in output.splitlines() if line.strip().startswith("- ")]


def test_n3_reserved_exits_zero(capsys):
    code = main(["reserved"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Reserved words in namel3ss" in out


def test_n3_reserved_lists_known_words(capsys):
    code = main(["reserved"])
    out = capsys.readouterr().out
    assert code == 0
    words = _collect_words(out)
    assert "title" in words
    assert "flow" in words
    assert words == sorted(words)


def test_n3_reserved_is_deterministic(capsys):
    code1 = main(["reserved"])
    out1 = capsys.readouterr().out
    code2 = main(["reserved"])
    out2 = capsys.readouterr().out
    assert code1 == 0
    assert code2 == 0
    assert out1 == out2
