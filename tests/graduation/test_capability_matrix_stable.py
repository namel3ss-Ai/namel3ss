from namel3ss.graduation.matrix import build_capability_matrix


def test_capability_matrix_stable() -> None:
    first = build_capability_matrix()
    second = build_capability_matrix()
    assert first == second
