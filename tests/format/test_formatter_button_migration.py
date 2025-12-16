from namel3ss.format.formatter import format_source


def test_button_migrates_to_block():
    source = 'page "home":\n  button "Run" calls flow "demo"\n'
    formatted = format_source(source)
    assert formatted == 'page "home":\n  button "Run":\n    calls flow "demo"\n'
