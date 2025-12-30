from __future__ import annotations

from namel3ss.module_loader import load_project


def run_exports(path: str, *, json_mode: bool) -> tuple[dict | None, str | None]:
    project = load_project(path)
    modules = project.modules
    if json_mode:
        payload = []
        for name in sorted(modules.keys()):
            exports = modules[name].exports.kinds()
            payload.append({"name": name, "exports": exports})
        return {"modules": payload}, None

    lines = []
    for name in sorted(modules.keys()):
        lines.append(f"{name}:")
        exports = modules[name].exports.kinds()
        if not exports:
            lines.append("  no exports")
            continue
        for kind in sorted(exports.keys()):
            symbols = ", ".join(exports[kind])
            lines.append(f"  {kind}: {symbols}")
    return None, "\n".join(lines)
