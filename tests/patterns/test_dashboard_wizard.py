from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.patterns.dashboard import DashboardPatternConfig, build_dashboard_pattern
from namel3ss.ui.patterns.wizard import WizardPatternConfig, build_wizard_pattern



def test_dashboard_pattern_is_deterministic() -> None:
    first = build_dashboard_pattern(DashboardPatternConfig(name="Ops Dashboard", metric_labels=("A", "B"), columns=2))
    second = build_dashboard_pattern(DashboardPatternConfig(name="Ops Dashboard", metric_labels=("A", "B"), columns=2))
    assert first == second



def test_dashboard_pattern_validates_columns() -> None:
    with pytest.raises(Namel3ssError):
        build_dashboard_pattern(DashboardPatternConfig(columns=0))



def test_wizard_pattern_is_deterministic() -> None:
    first = build_wizard_pattern(WizardPatternConfig(name="Onboarding", sections=("A", "B")))
    second = build_wizard_pattern(WizardPatternConfig(name="Onboarding", sections=("A", "B")))
    assert first == second



def test_wizard_pattern_requires_sections() -> None:
    with pytest.raises(Namel3ssError):
        build_wizard_pattern(WizardPatternConfig(sections=()))
