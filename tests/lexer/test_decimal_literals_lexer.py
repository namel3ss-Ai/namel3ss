from decimal import Decimal

from namel3ss.lexer.lexer import Lexer


def test_lexer_tokenizes_decimal_number_as_single_token():
    source = 'flow "demo":\n  let x is 10.50\n'
    tokens = Lexer(source).tokenize()
    numbers = [tok.value for tok in tokens if tok.type == "NUMBER"]
    assert numbers == [Decimal("10.50")]
