from __future__ import annotations

import difflib

from namel3ss.errors.guidance import build_guidance_message


def unknown_flow_message(name: str, flow_names: set[str], page_name: str) -> str:
    suggestion = difflib.get_close_matches(name, flow_names, n=1, cutoff=0.6)
    hint = f' Did you mean "{suggestion[0]}"?' if suggestion else ""
    available = sorted(flow_names)
    sample = ", ".join(available[:5]) if available else "none defined"
    if len(available) > 5:
        sample += ", ..."
    why = f"The app defines flows: {sample}." if available else "The app does not define any flows."
    example = (
        f'button "Run":\\n  calls flow "{available[0]}"'
        if available
        else 'flow "demo"\\n  input\\n    name is text'
    )
    return build_guidance_message(
        what=f"Page '{page_name}' references unknown flow '{name}'.{hint}",
        why=why,
        fix='Use `calls flow "<name>"` with an existing flow name.',
        example=example,
    )


__all__ = ["unknown_flow_message"]
