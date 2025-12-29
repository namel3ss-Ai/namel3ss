from namel3ss.parser.core import parse


def test_use_statement_parses():
    source = 'spec is "1.0"\n\nuse "inventory" as inv\nflow "demo":\n  return "ok"\n'
    program = parse(source)
    assert len(program.uses) == 1
    assert program.uses[0].module == "inventory"
    assert program.uses[0].alias == "inv"
