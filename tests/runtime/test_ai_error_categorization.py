from namel3ss.runtime.ai.providers._shared.diagnostics import categorize_ai_error


def _assert_clean_hint(hint: str) -> None:
    assert "sk-" not in hint
    assert "Bearer" not in hint


def test_categorize_auth():
    result = categorize_ai_error({"status": 401, "message": "Unauthorized"})
    assert result["category"] == "auth"
    _assert_clean_hint(result["hint"])


def test_categorize_model_access():
    result = categorize_ai_error({"code": "model_not_found", "message": "model not found"})
    assert result["category"] == "model_access"
    _assert_clean_hint(result["hint"])


def test_categorize_rate_limit():
    result = categorize_ai_error({"status": 429, "message": "rate limit exceeded"})
    assert result["category"] == "rate_limit"
    _assert_clean_hint(result["hint"])


def test_categorize_server_error():
    result = categorize_ai_error({"status": 503, "message": "service unavailable"})
    assert result["category"] == "server"
    _assert_clean_hint(result["hint"])


def test_categorize_network_error():
    result = categorize_ai_error({"message": "unreachable"})
    assert result["category"] == "network"
    _assert_clean_hint(result["hint"])


def test_categorize_timeout_error():
    result = categorize_ai_error(
        {"message": "unreachable", "network_error": {"name": "TimeoutError", "message": "timed out"}}
    )
    assert result["category"] == "timeout"
    _assert_clean_hint(result["hint"])
