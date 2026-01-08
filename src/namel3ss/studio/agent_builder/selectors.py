from __future__ import annotations

from namel3ss.ir import nodes as ir
from namel3ss.studio.agent_builder.templates import list_pattern_metadata, list_memory_presets
from namel3ss.runtime.memory_packs import list_available_packs, load_memory_pack_catalog, pack_provides


def list_agents(program: ir.Program) -> list[dict]:
    agents = sorted(program.agents.values(), key=lambda agent: agent.name)
    return [
        {
            "name": agent.name,
            "ai_name": agent.ai_name,
            "system_prompt": agent.system_prompt or "",
        }
        for agent in agents
    ]


def list_ai_profiles(program: ir.Program) -> list[dict]:
    profiles = sorted(program.ais.values(), key=lambda profile: profile.name)
    data = []
    for profile in profiles:
        memory = getattr(profile, "memory", None)
        data.append(
            {
                "name": profile.name,
                "provider": profile.provider or "",
                "model": profile.model,
                "system_prompt": profile.system_prompt or "",
                "tools": list(profile.exposed_tools or []),
                "memory": {
                    "short_term": getattr(memory, "short_term", 0),
                    "semantic": bool(getattr(memory, "semantic", False)),
                    "profile": bool(getattr(memory, "profile", False)),
                },
            }
        )
    return data


def list_tools(program: ir.Program) -> list[dict]:
    tools = sorted(program.tools.values(), key=lambda tool: tool.name)
    return [
        {
            "name": tool.name,
            "kind": tool.kind,
            "input_fields": [field.name for field in tool.input_fields],
        }
        for tool in tools
    ]


def list_patterns() -> list[dict]:
    return list_pattern_metadata()


def list_memory_options() -> list[dict]:
    return list_memory_presets()


def list_memory_packs(*, project_root: str | None, app_path: str | None) -> list[dict]:
    catalog = load_memory_pack_catalog(project_root=project_root, app_path=app_path)
    builtin_ids = {pack.pack_id for pack in catalog.builtin}
    local_ids = {pack.pack_id for pack in catalog.local}
    data: list[dict] = []
    for pack in list_available_packs(catalog):
        if pack.pack_id in builtin_ids:
            source = "builtin"
        elif pack.pack_id in local_ids:
            source = "local"
        else:
            source = "unknown"
        data.append(
            {
                "id": pack.pack_id,
                "name": pack.pack_name,
                "version": pack.pack_version,
                "provides": pack_provides(pack),
                "source": source,
            }
        )
    return data


__all__ = [
    "list_agents",
    "list_ai_profiles",
    "list_memory_packs",
    "list_tools",
    "list_patterns",
    "list_memory_options",
]
