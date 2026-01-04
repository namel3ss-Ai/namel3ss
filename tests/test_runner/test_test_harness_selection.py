from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.test_runner.parser import parse_test_file
from namel3ss.test_runner.runner import discover_test_files


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discover_test_files_ignores_non_test_files(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    _write(
        tests_dir / "smoke_test.ai",
        'test "smoke":\n'
        '  run flow "demo" with input: {} as result\n'
        '  expect value is "ok"\n',
    )
    _write(tests_dir / "readme.ai", 'spec is "1.0"\n')
    found = discover_test_files(tmp_path)
    assert [path.name for path in found] == ["smoke_test.ai"]


def test_parse_test_file_rejects_spec_declaration(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "bad_test.ai"
    _write(
        test_file,
        'spec is "1.0"\n'
        'test "smoke":\n'
        '  run flow "demo" with input: {} as result\n'
        '  expect value is "ok"\n',
    )
    with pytest.raises(Namel3ssError) as exc:
        parse_test_file(test_file)
    assert "Unexpected line in test file" in str(exc.value)
