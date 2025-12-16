from namel3ss.parser import statements as st


def test_statements_facade_exports() -> None:
    expected = [
        "parse_statement",
        "parse_if",
        "parse_match",
        "parse_save",
        "parse_find",
        "parse_target",
        "validate_match_pattern",
    ]
    for name in expected:
        assert hasattr(st, name), f"Facade missing {name}"
