from __future__ import annotations

from pathlib import Path

from namel3ss import contract as build_contract
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore


EXPENSE_APP = Path("examples/demos/expense_tracker/app.ai")
INVENTORY_APP = Path("examples/demos/inventory_orders/app.ai")


def test_expense_totals_recompute_clears_previous_rows() -> None:
    contract_obj = build_contract(EXPENSE_APP.read_text(encoding="utf-8"))
    program = contract_obj.program
    store = MemoryStore()
    execute_program_flow(program, "seed_expenses", store=store)
    execute_program_flow(program, "recompute_totals", store=store)

    totals_schema = next(record for record in program.records if record.name == "CategoryTotal")
    first_totals = store.list_records(totals_schema)
    assert len(first_totals) == 4

    execute_program_flow(program, "recompute_totals", store=store)
    second_totals = store.list_records(totals_schema)
    assert len(second_totals) == 4


def test_inventory_updates_apply_in_place() -> None:
    contract_obj = build_contract(INVENTORY_APP.read_text(encoding="utf-8"))
    program = contract_obj.program
    store = MemoryStore()

    execute_program_flow(program, "seed_products", store=store)
    execute_program_flow(
        program,
        "place_order",
        store=store,
        input={"values": {"id": 200, "sku": "SKU-100", "quantity": 2}},
    )

    inventory_schema = next(record for record in program.records if record.name == "Inventory")
    inventory_rows = store.find(inventory_schema, {"sku": "SKU-100"})
    assert len(inventory_rows) == 1
    assert inventory_rows[0]["quantity"] == 8

    execute_program_flow(program, "fulfill_order", store=store, input={"values": {"id": 200}})

    orders_schema = next(record for record in program.records if record.name == "Order")
    orders = store.find(orders_schema, {"id": 200})
    assert len(orders) == 1
    assert orders[0]["status"] == "Fulfilled"
