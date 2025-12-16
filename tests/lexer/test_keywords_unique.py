from namel3ss.lexer.tokens import KEYWORDS


def test_keywords_have_unique_entries() -> None:
    assert len(KEYWORDS) == len(set(KEYWORDS.keys()))


def test_keywords_have_token_types() -> None:
    assert all(isinstance(token_type, str) and token_type for token_type in KEYWORDS.values())
