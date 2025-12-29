from __future__ import annotations

from pathlib import Path

from namel3ss.contract.model import Contract, ContractPack
from namel3ss.contract.normalize import (
    build_plain_text,
    derive_capabilities_required,
    derive_features_used,
    write_contract_artifacts,
)
from namel3ss.contract.render_plain import render_exists
from namel3ss.ir.model.program import Program


def build_contract_pack(contract: Contract) -> ContractPack:
    program_summary = _build_program_summary(contract.program)
    features_used = list(derive_features_used(contract.program))
    capabilities_required = list(derive_capabilities_required(contract.program))
    warnings = _build_warnings(program_summary)

    pack = ContractPack(
        spec_version=contract.spec_version,
        source_hash=contract.source_hash,
        program_summary=program_summary,
        features_used=features_used,
        capabilities_required=capabilities_required,
        warnings=warnings,
        time_utc=None,
    )

    payload = pack.as_dict()
    plain_text = build_plain_text(payload)
    text = render_exists(pack)
    write_contract_artifacts(_resolve_root(contract.program), payload, plain_text, text)
    return pack


def _build_program_summary(program: Program) -> dict[str, object]:
    flows = sorted({flow.name for flow in program.flows})
    records = sorted({record.name for record in program.records})
    pages = sorted({page.name for page in program.pages})
    ais = sorted(program.ais.keys())
    tools = sorted(program.tools.keys())
    agents = sorted(program.agents.keys())
    identity = program.identity
    return {
        "flows": {"count": len(flows), "names": flows},
        "records": {"count": len(records), "names": records},
        "pages": {"count": len(pages), "names": pages},
        "ais": {"count": len(ais), "names": ais},
        "tools": {"count": len(tools), "names": tools},
        "agents": {"count": len(agents), "names": agents},
        "identity": {
            "present": identity is not None,
            "name": identity.name if identity is not None else None,
        },
    }


def _build_warnings(program_summary: dict[str, object]) -> list[str]:
    warnings: list[str] = []
    flows = program_summary.get("flows") or {}
    tools = program_summary.get("tools") or {}
    ais = program_summary.get("ais") or {}
    flow_count = flows.get("count") if isinstance(flows, dict) else 0
    tool_count = tools.get("count") if isinstance(tools, dict) else 0
    ai_count = ais.get("count") if isinstance(ais, dict) else 0

    if not flow_count:
        warnings.append("No flows defined.")
    if isinstance(flow_count, int) and flow_count > 10:
        warnings.append("Many flows defined; start with one flow for clarity.")
    if isinstance(tool_count, int) and tool_count > 0:
        warnings.append("Tools are declared; runtime may require tool bindings depending on runner.")
    if isinstance(ai_count, int) and ai_count > 0:
        warnings.append("AI profiles are declared; runtime requires an AI provider.")
    return warnings


def _resolve_root(program: Program) -> Path:
    project_root = getattr(program, "project_root", None)
    if isinstance(project_root, Path):
        return project_root
    if isinstance(project_root, str) and project_root:
        return Path(project_root)

    app_path = getattr(program, "app_path", None)
    if isinstance(app_path, Path):
        return app_path.parent
    if isinstance(app_path, str) and app_path:
        return Path(app_path).parent

    return Path.cwd()


__all__ = ["build_contract_pack"]
