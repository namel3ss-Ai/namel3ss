from namel3ss.observe.log import read_events, record_event


def test_observe_redacts_secrets(tmp_path):
    secret = "super-secret-value"
    record_event(tmp_path, {"type": "engine_error", "message": secret}, secret_values=[secret])
    events = read_events(tmp_path)
    assert events[0]["message"] == "***REDACTED***"
