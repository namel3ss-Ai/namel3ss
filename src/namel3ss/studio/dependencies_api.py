from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.unified_manager import (
    dependency_add,
    dependency_audit,
    dependency_clean,
    dependency_install,
    dependency_status,
    dependency_tree,
    dependency_update,
    dependency_verify,
)
from namel3ss.pkg.runtime_manifest_ops import remove_runtime_dependency
from namel3ss.runtime.capabilities.feature_gate import require_app_capability


DEPENDENCY_MANAGEMENT_CAPABILITY = "dependency_management"


def get_dependencies_payload(source: str, app_path: str) -> dict[str, object]:
    del source
    app_file = Path(app_path)
    root = app_file.parent
    status = dependency_status(root)
    try:
        status["tree"] = dependency_tree(root)
    except Namel3ssError:
        status["tree"] = {
            "status": "ok",
            "package_tree": [],
            "runtime_python": [],
            "runtime_system": [],
        }
    return {
        "ok": True,
        "status": status,
    }


def apply_dependencies_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    del source
    app_file = Path(app_path)
    root = app_file.parent
    action = str(body.get("action") or "status").strip().lower()

    if action in {"status", "tree"}:
        payload = dependency_status(root) if action == "status" else dependency_tree(root)
        payload["action"] = action
        return payload

    _require_dependency_capability(app_file)

    if action == "install":
        return dependency_install(
            root,
            python_override=_optional_text(body.get("python")),
            include_packages=bool(body.get("include_packages", True)),
            include_python=bool(body.get("include_python", True)),
        )
    if action == "update":
        return dependency_update(root, python_override=_optional_text(body.get("python")))
    if action == "verify":
        return dependency_verify(root)
    if action == "audit":
        return dependency_audit(root)
    if action == "clean":
        return dependency_clean(root, include_venv=bool(body.get("include_venv", False)))
    if action == "add_python":
        spec = _required_text(body.get("spec"), field="spec")
        return dependency_add(root, spec=spec, dependency_type="python")
    if action == "add_system":
        spec = _required_text(body.get("spec"), field="spec")
        return dependency_add(root, spec=spec, dependency_type="system")
    if action == "remove_python":
        spec = _required_text(body.get("spec"), field="spec")
        return remove_runtime_dependency(root, spec=spec, dependency_type="python")
    if action == "remove_system":
        spec = _required_text(body.get("spec"), field="spec")
        return remove_runtime_dependency(root, spec=spec, dependency_type="system")

    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown dependencies action '{action}'.",
            why=(
                "Supported actions are status, tree, install, update, verify, audit, clean, "
                "add_python, add_system, remove_python, and remove_system."
            ),
            fix="Use a supported action in the Studio dependencies payload.",
            example='{"action":"install"}',
        )
    )


def _require_dependency_capability(app_file: Path) -> None:
    require_app_capability(app_file, DEPENDENCY_MANAGEMENT_CAPABILITY)


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _required_text(value: object, *, field: str) -> str:
    text = _optional_text(value)
    if text:
        return text
    raise Namel3ssError(
        build_guidance_message(
            what=f"Missing required field '{field}'.",
            why=f"Dependencies action requires '{field}' to be a non-empty string.",
            fix=f"Provide '{field}' in the request body.",
            example='{"action":"add_python","spec":"requests@2.31.0"}',
        )
    )


__all__ = ["apply_dependencies_payload", "get_dependencies_payload"]
