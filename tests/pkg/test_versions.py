from namel3ss.pkg.versions import Semver, parse_constraint


def test_exact_constraint_matches_only_exact():
    constraint = parse_constraint("=0.1.2")
    assert constraint.matches(Semver(0, 1, 2))
    assert not constraint.matches(Semver(0, 1, 3))


def test_caret_constraint_matches_range():
    constraint = parse_constraint("^0.1")
    assert constraint.matches(Semver(0, 1, 0))
    assert constraint.matches(Semver(0, 1, 9))
    assert not constraint.matches(Semver(0, 2, 0))


def test_tilde_constraint_matches_minor_range():
    constraint = parse_constraint("~0.1.2")
    assert constraint.matches(Semver(0, 1, 2))
    assert constraint.matches(Semver(0, 1, 9))
    assert not constraint.matches(Semver(0, 2, 0))
