import sys
import subprocess
import pytest
from namel3ss.cli.main import main

def test_module_execution():
    """
    Verifies that `python -m namel3ss --help` works.
    This is the fallback guarantee for Windows users with broken PATHs.
    """
    result = subprocess.run(
        [sys.executable, "-m", "namel3ss", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "n3 new" in result.stdout

def test_cli_main_import_safety():
    """
    Verifies that importing the CLI main module doesn't trigger side effects.
    """
    # This test is implicit because if import caused execution,
    # the test runner would have side effects or exit.
    # We explicitly check that main() exists and is callable.
    assert callable(main)

def test_cli_return_code():
    """
    Verifies main() returns an int code (0 for help).
    """
    ret = main(["--help"])
    assert isinstance(ret, int)
    assert ret == 0
