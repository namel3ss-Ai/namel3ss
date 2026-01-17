from namel3ss.parser.core import parse


def test_use_module_parses_blocks():
    source = (
        'spec is "1.0"\n\n'
        'use module "modules/common.ai" as common\n'
        'only:\n'
        '  functions\n'
        '  records\n'
        '  jobs\n'
        'allow override:\n'
        '  tools\n\n'
        'flow "demo":\n'
        '  return "ok"\n'
    )
    program = parse(source)
    assert len(program.uses) == 1
    use = program.uses[0]
    assert use.module == "modules/common.ai"
    assert use.module_path == "modules/common.ai"
    assert use.alias == "common"
    assert use.only == ["functions", "records", "jobs"]
    assert use.allow_override == ["tools"]
