from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss import contract as build_contract
from namel3ss.ir.model.pages import ButtonItem, CardItem, ColumnItem, RowItem, SectionItem


DEMO_APPS = [
    Path("examples/demos/task_manager/app.ai"),
    Path("examples/demos/expense_tracker/app.ai"),
    Path("examples/demos/inventory_orders/app.ai"),
    Path("examples/demos/weather_dashboard/app.ai"),
    Path("examples/demos/currency_converter/app.ai"),
]


def _iter_buttons(items: list[object]) -> list[ButtonItem]:
    buttons: list[ButtonItem] = []
    for item in items:
        if isinstance(item, ButtonItem):
            buttons.append(item)
            continue
        if isinstance(item, (SectionItem, CardItem, RowItem, ColumnItem)):
            buttons.extend(_iter_buttons(item.children))
    return buttons


@pytest.mark.parametrize("app_path", DEMO_APPS)
def test_demo_contracts_are_valid(app_path: Path) -> None:
    source = app_path.read_text(encoding="utf-8")
    contract_obj = build_contract(source)
    contract_obj.validate()
    assert contract_obj.program.pages, f"{app_path} has no pages"
    assert contract_obj.program.flows, f"{app_path} has no flows"
    flow_names = {flow.name for flow in contract_obj.program.flows}
    buttons: list[ButtonItem] = []
    for page in contract_obj.program.pages:
        buttons.extend(_iter_buttons(page.items))
    for button in buttons:
        assert button.flow_name in flow_names, f"{app_path} button calls missing flow {button.flow_name}"
