from tools.ui_baseline_refresh import build_baseline_payloads


def test_ui_baseline_refresh_is_deterministic() -> None:
    first = build_baseline_payloads()
    second = build_baseline_payloads()
    assert first == second
