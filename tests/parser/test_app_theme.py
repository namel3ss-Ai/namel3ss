from namel3ss.parser.core import parse
from tests.conftest import lower_ir_program


def test_parse_app_theme_dark():
    source = 'spec is "1.0"\n\napp:\n  theme is "dark"\nflow "demo":\n  return "ok"\n'
    ast_prog = parse(source)
    assert ast_prog.app_theme == "dark"
    ir_prog = lower_ir_program(source)
    assert ir_prog.theme == "dark"


def test_default_theme_system():
    source = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'
    ir_prog = lower_ir_program(source)
    assert ir_prog.theme == "light"


def test_invalid_theme_lints():
    source = 'spec is "1.0"\n\napp:\n  theme is "neon"\nflow "demo":\n  return "ok"\n'
    from namel3ss.lint.engine import lint_source

    findings = lint_source(source)
    assert any(f.code == "app.invalid_theme" for f in findings)


def test_theme_tokens_parse_and_lower():
    source = 'spec is "1.0"\n\napp:\n  theme is "system"\n  theme_tokens:\n    surface is "raised"\n    accent is "secondary"\nflow "demo":\n  return "ok"\n'
    ir_prog = lower_ir_program(source)
    assert ir_prog.theme_tokens.get("surface") == "raised"
    assert ir_prog.theme_tokens.get("accent") == "secondary"


def test_theme_tokens_invalid_name():
    source = 'spec is "1.0"\n\napp:\n  theme_tokens:\n    unknown is "primary"\nflow "demo":\n  return "ok"\n'
    from namel3ss.lint.engine import lint_source

    findings = lint_source(source)
    assert any(f.code == "app.invalid_theme_token" for f in findings)


def test_theme_tokens_invalid_value():
    source = 'spec is "1.0"\n\napp:\n  theme_tokens:\n    surface is "neon"\nflow "demo":\n  return "ok"\n'
    from namel3ss.lint.engine import lint_source

    findings = lint_source(source)
    assert any(f.code == "app.invalid_theme_token_value" for f in findings)
