from pathlib import Path
import socket

from namel3ss.cli.main import main
from namel3ss.runtime.service_runner import ServiceRunner

FORBIDDEN_TERMS = (
    "ir",
    "contract",
    "capability",
    "pack",
    "boundary",
    "proof",
    "capsule",
    "governance",
    "spec",
)


def _assert_no_forbidden_terms(text: str) -> None:
    lower = text.lower()
    for term in FORBIDDEN_TERMS:
        assert term not in lower


def _write_basic_app(root: Path) -> None:
    (root / "app.ai").write_text(
        'spec is "1.0"\n\n'
        "capabilities:\n"
        "  service\n\n"
        'record "Order":\n'
        '  field "id" is number must be present\n\n'
        'record "Answer":\n'
        '  field "text" is text must be present\n\n'
        'tool "echo":\n'
        '  implemented using builtin\n\n'
        '  input:\n'
        '    value is json\n\n'
        '  output:\n'
        '    echo is json\n\n'
        'ai "assistant":\n'
        '  provider is "mock"\n'
        '  model is "gpt-4.1"\n\n'
        'flow "ask_flow":\n'
        '  return "ok"\n\n'
        'flow "review_flow":\n'
        '  return "ok"\n\n'
        'page "Home":\n'
        '  title is "Demo"\n',
        encoding="utf-8",
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("0.0.0.0", 0))
        return int(sock.getsockname()[1])


def test_first_run_error_output_is_clean(tmp_path, monkeypatch, capsys):
    _write_basic_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("N3_FIRST_RUN", "1")
    code = main(["why", "--badflag"])
    err = capsys.readouterr().err.strip()
    assert code == 1
    assert "Something went wrong" in err
    assert "What happened" in err
    assert "Why" in err
    assert "How to resolve it" in err
    assert "Suggested next step" in err
    _assert_no_forbidden_terms(err)


def test_first_run_why_output_is_stable(tmp_path, monkeypatch, capsys):
    _write_basic_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("N3_FIRST_RUN", "1")
    code = main(["why"])
    out = capsys.readouterr().out.strip().splitlines()
    assert code == 0
    assert out == [
        "What this app does",
        "- Provides 1 screen with 2 actions.",
        "- Screens include: Home.",
        "What data it works with",
        "- Records: Answer, Order.",
        "How AI is involved",
        "- Uses AI profiles: assistant.",
        "External tools",
        "- Tool integrations: echo.",
    ]
    _assert_no_forbidden_terms("\n".join(out))


def test_first_run_demo_run_output(tmp_path, monkeypatch, capsys):
    _write_basic_app(tmp_path)
    (tmp_path / ".namel3ss").mkdir()
    (tmp_path / ".namel3ss" / "demo.json").write_text('{"name":"demo"}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ServiceRunner, "start", lambda *args, **kwargs: None)
    port = _free_port()
    code = main(["run", "--port", str(port)])
    out = capsys.readouterr().out.strip().splitlines()
    assert code == 0
    assert out == [
        "Running demo",
        f"Open: http://127.0.0.1:{port}/",
        "Press Ctrl+C to stop",
    ]


def test_run_demo_opens_url_disabled_in_ci(tmp_path, monkeypatch, capsys):
    _write_basic_app(tmp_path)
    (tmp_path / ".namel3ss").mkdir()
    (tmp_path / ".namel3ss" / "demo.json").write_text('{"name":"demo"}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CI", "1")
    monkeypatch.setattr("namel3ss.cli.open_url._has_tty", lambda *args, **kwargs: True)
    monkeypatch.setattr(ServiceRunner, "start", lambda *args, **kwargs: None)
    opened = {"count": 0}

    def fake_open_url(_url: str) -> bool:
        opened["count"] += 1
        return True

    monkeypatch.setattr("namel3ss.cli.run_mode.open_url", fake_open_url)
    code = main(["run", "--port", str(_free_port())])
    capsys.readouterr()
    assert code == 0
    assert opened["count"] == 0
