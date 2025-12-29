from namel3ss.runtime.executor.api import execute_program_flow
from tests.conftest import lower_ir_program


def test_theme_change_executes_without_state_mutation():
    source = 'spec is "1.0"\n\nflow "demo":\n  set theme to "dark"\n'
    program_ir = lower_ir_program(source)
    result = execute_program_flow(program_ir, "demo", state={}, input={})
    assert result.state == {}
    assert result.runtime_theme == "dark"
    assert any(getattr(t, "get", lambda k, d=None: None)("type") == "theme_change" if isinstance(t, dict) else getattr(t, "type", None) == "theme_change" for t in result.traces)
