from tests.conftest import parse_program


def test_theme_preference_defaults():
    program = parse_program('app:\n  theme is "system"\n')
    pref = program.theme_preference
    assert pref["allow_override"][0] is False
    assert pref["persist"][0] == "none"


def test_theme_preference_parse_block():
    source = 'app:\n  theme is "light"\n  theme_preference:\n    allow_override is true\n    persist is "file"\n'
    program = parse_program(source)
    pref = program.theme_preference
    assert pref["allow_override"][0] is True
    assert pref["persist"][0] == "file"
