from namel3ss.runtime.memory.proof.normalize import normalize_value


def test_normalize_is_stable() -> None:
    payload = {
        "b": 2,
        "a": {"d": 4, "c": 3},
        "list": [{"z": 1, "y": 2}],
    }
    first = normalize_value(payload)
    second = normalize_value(first)
    assert first == second
