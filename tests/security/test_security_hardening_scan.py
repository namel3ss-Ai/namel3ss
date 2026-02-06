from __future__ import annotations

from pathlib import Path

from namel3ss.security_hardening_scan import run_security_hardening_scan


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_security_scan_passes_for_safe_code(tmp_path: Path) -> None:
    _write(
        tmp_path / "src" / "safe.py",
        "import subprocess\n"
        "\n"
        "def run() -> None:\n"
        "    subprocess.run([\"echo\", \"ok\"], check=False)\n",
    )
    _write(tmp_path / "docs" / "readme.md", "No secrets here.\n")

    report = run_security_hardening_scan(tmp_path)
    assert report.status == "pass"
    assert report.issues == ()


def test_security_scan_flags_unsafe_execution_patterns(tmp_path: Path) -> None:
    _write(
        tmp_path / "src" / "unsafe.py",
        "import os\n"
        "import subprocess\n"
        "\n"
        "def run(value: str) -> None:\n"
        "    eval(value)\n"
        "    exec(value)\n"
        "    os.system(\"echo hi\")\n"
        "    subprocess.run(\"echo hi\", shell=True, check=False)\n",
    )

    report = run_security_hardening_scan(tmp_path)
    issue_types = [issue.issue_type for issue in report.issues]
    assert issue_types == sorted(issue_types)
    assert "dynamic_eval" in issue_types
    assert "dynamic_exec" in issue_types
    assert "os_system_call" in issue_types
    assert "subprocess_shell_true" in issue_types
    assert "subprocess_string_command" in issue_types


def test_security_scan_flags_secret_patterns(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs" / "secrets.md",
        "OpenAI key sk-abcdefghijklmnopqrstuvwxyzABCDEFG123456\n"
        "AWS key AKIAABCDEFGHIJKLMNOP\n",
    )

    report = run_security_hardening_scan(tmp_path)
    assert report.status == "fail"
    assert [issue.issue_type for issue in report.issues] == ["secret_pattern", "secret_pattern"]
    assert report.issues[0].line == 1
    assert report.issues[1].line == 2


def test_security_scan_report_is_path_and_line_sorted(tmp_path: Path) -> None:
    _write(tmp_path / "src" / "z.py", "def run(v):\n    eval(v)\n")
    _write(tmp_path / "src" / "a.py", "def run(v):\n    exec(v)\n")

    report = run_security_hardening_scan(tmp_path)
    assert [(issue.path, issue.line, issue.issue_type) for issue in report.issues] == [
        ("src/a.py", 2, "dynamic_exec"),
        ("src/z.py", 2, "dynamic_eval"),
    ]


def test_security_scan_covers_tests_modules(tmp_path: Path) -> None:
    _write(tmp_path / "tests" / "unsafe_eval.py", "def run(v):\n    eval(v)\n")
    report = run_security_hardening_scan(tmp_path)
    assert any(issue.path == "tests/unsafe_eval.py" and issue.issue_type == "dynamic_eval" for issue in report.issues)
