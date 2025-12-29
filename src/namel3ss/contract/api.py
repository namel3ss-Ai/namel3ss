from __future__ import annotations

import hashlib

from namel3ss.contract.model import Contract
from namel3ss.contract.normalize import (
    derive_capabilities_required,
    derive_features_used,
    derive_flow_names,
)
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.lowering.program import lower_program
from namel3ss.ir.model.pages import ButtonItem, CardItem, ColumnItem, PageItem, RowItem, SectionItem
from namel3ss.parser.core import Parser
from namel3ss.runtime.executor.api import execute_program_flow


def contract(
    source: str,
    *,
    allow_capsule: bool = False,
    allow_legacy_type_aliases: bool = True,
) -> Contract:
    ast_program = Parser.parse(
        source,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        allow_capsule=allow_capsule,
    )
    program_ir = lower_program(ast_program)
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return Contract(
        spec_version=program_ir.spec_version,
        source_hash=source_hash,
        program=program_ir,
        features_used=derive_features_used(program_ir),
        capabilities_required=derive_capabilities_required(program_ir),
        flow_names=derive_flow_names(program_ir),
    )


def validate(contract_obj: Contract) -> None:
    validate_contract(contract_obj)


def validate_contract(contract_obj: Contract) -> None:
    program = contract_obj.program
    flows = program.flows
    if not flows:
        raise Namel3ssError(
            build_guidance_message(
                what="No flows defined.",
                why="At least one flow is required to run an app.",
                fix="Add a flow block to app.ai.",
                example='flow "main": return "ok"',
            )
        )

    seen: dict[str, object] = {}
    for flow in flows:
        if flow.name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate flow name '{flow.name}'.",
                    why="Flow names must be unique.",
                    fix="Rename one of the flows so each name is unique.",
                    example=f'flow "{flow.name}": return "ok"',
                ),
                line=flow.line,
                column=flow.column,
            )
        seen[flow.name] = flow

    flow_names = set(seen.keys())
    for page in program.pages:
        for button in _iter_page_buttons(page.items):
            if button.flow_name not in flow_names:
                available = sorted(flow_names)
                sample = ", ".join(available[:5]) if available else "none defined"
                why = f"The app defines flows: {sample}." if available else "The app does not define any flows."
                example = (
                    f'button "{button.label}":\\n  calls flow "{available[0]}"'
                    if available
                    else 'flow "main": return "ok"'
                )
                raise Namel3ssError(
                    build_guidance_message(
                        what=f"Page button calls missing flow '{button.flow_name}'.",
                        why=why,
                        fix="Update the button to call an existing flow or add the missing flow.",
                        example=example,
                    ),
                    line=button.line,
                    column=button.column,
                )


def run_contract(
    contract_obj: Contract,
    flow: str,
    *,
    state: dict | None = None,
    input: dict | None = None,
    store=None,
    ai_provider=None,
    memory_manager=None,
    runtime_theme: str | None = None,
    identity: dict | None = None,
):
    return execute_program_flow(
        contract_obj.program,
        flow,
        state=state,
        input=input,
        store=store,
        ai_provider=ai_provider,
        memory_manager=memory_manager,
        runtime_theme=runtime_theme,
        identity=identity,
    )


def _iter_page_buttons(items: list[PageItem]) -> list[ButtonItem]:
    buttons: list[ButtonItem] = []
    for item in items:
        if isinstance(item, ButtonItem):
            buttons.append(item)
            continue
        if isinstance(item, (SectionItem, CardItem, RowItem, ColumnItem)):
            buttons.extend(_iter_page_buttons(item.children))
    return buttons


__all__ = ["contract", "run_contract", "validate", "validate_contract"]
