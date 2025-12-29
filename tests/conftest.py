import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from namel3ss.ir.nodes import lower_program  # noqa: E402
from namel3ss.parser.core import parse  # noqa: E402
from namel3ss.runtime.executor import Executor  # noqa: E402


def _ensure_spec(code: str) -> str:
    for line in code.splitlines():
        if line.strip().startswith('spec is "'):
            return code
    return 'spec is "1.0"\n\n' + code.lstrip("\n")


def parse_program(code: str):
    """Parse source into an AST program."""
    return parse(_ensure_spec(code))


def lower_ir_program(code: str):
    """Parse then lower to IR Program."""
    return lower_program(parse_program(code))


def run_flow(
    code: str,
    flow_name: str = "demo",
    initial_state=None,
    store=None,
    identity=None,
    input_data=None,
):
    """Parse, lower, and execute a flow by name."""
    ir_program = lower_ir_program(code)
    flow = next((f for f in ir_program.flows if f.name == flow_name), None)
    if flow is None:
        raise ValueError(f"Flow '{flow_name}' not found")
    schemas = {schema.name: schema for schema in ir_program.records}
    executor = Executor(
        flow,
        schemas=schemas,
        initial_state=initial_state,
        store=store,
        input_data=input_data,
        functions=ir_program.functions,
        runtime_theme=getattr(ir_program, "theme", None),
        identity_schema=getattr(ir_program, "identity", None),
        identity=identity,
    )
    return executor.run()


@pytest.fixture(autouse=True)
def _secret_audit_path(tmp_path, monkeypatch):
    monkeypatch.setenv("N3_SECRET_AUDIT_PATH", str(tmp_path / "secret_audit.jsonl"))


__all__ = ["parse_program", "lower_ir_program", "run_flow"]
