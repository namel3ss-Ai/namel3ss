from __future__ import annotations

from namel3ss.cli.main import main as cli_main


SOURCE = '''spec is "1.0"
use preset "rag_chat":
  title is "Assistant"
  model is "gpt-4o-mini"
  answer_template is "summary_keypoints_recommendation_with_citations"
'''


def test_expand_outputs_deterministic_rag_chat_template_source(tmp_path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")

    assert cli_main(["expand", app_path.as_posix()]) == 0
    first = capsys.readouterr().out
    assert 'ai "__rag_answer_ai":' in first
    assert 'flow "rag.answer": requires true' in first
    assert 'ask ai "__rag_answer_ai" with structured input from map:' in first

    assert cli_main(["expand", app_path.as_posix()]) == 0
    second = capsys.readouterr().out
    assert first == second


def test_expand_uses_default_app_path_when_not_provided(tmp_path, monkeypatch, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli_main(["expand"]) == 0
    output = capsys.readouterr().out
    assert output.startswith('spec is "1.0"\n')
    assert 'use preset "rag_chat"' not in output


def test_expand_rejects_unknown_flags(tmp_path, monkeypatch, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli_main(["expand", "--json"]) == 1
    err = capsys.readouterr().err
    assert "Unknown flag '--json'" in err


def test_expand_supports_app_first_command_shape(tmp_path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")

    assert cli_main([app_path.as_posix(), "expand"]) == 0
    output = capsys.readouterr().out
    assert 'use preset "rag_chat"' not in output
