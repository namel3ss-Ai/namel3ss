from namel3ss.config.loader import load_config
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.studio.api import get_actions_payload, get_ui_payload
from namel3ss.studio.session import SessionState
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

identity "user":
  trust_level is one of ["admin", "user"]

record "Metrics":
  value number

flow "send":
  return "ok"

page "home": requires identity.trust_level is "admin"
  table is "Metrics"
  chat:
    messages from is state.chat.messages
    composer calls flow "send"
    thinking when is state.chat.thinking
    citations from is state.chat.citations
    memory from is state.chat.memory
  chart from is state.metrics
  button "Send":
    calls flow "send"
'''


def _normalize_warnings(warnings: list) -> list[dict]:
    normalized = []
    for warning in warnings:
        entry = warning.to_dict() if hasattr(warning, "to_dict") else dict(warning)
        normalized.append(
            {
                "code": entry.get("code"),
                "message": entry.get("message"),
                "category": entry.get("category"),
                "enforced_at": entry.get("enforced_at"),
            }
        )
    return sorted(normalized, key=lambda item: item["code"] or "")


def test_studio_static_matches_cli_warnings(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    program = lower_ir_program(SOURCE)
    config = load_config(app_path=app_path)

    cli_warnings = []
    identity = resolve_identity(config, getattr(program, "identity", None), mode=ValidationMode.STATIC, warnings=cli_warnings)
    cli_manifest = build_manifest(
        program,
        state={},
        identity=identity,
        mode=ValidationMode.STATIC,
        warnings=cli_warnings,
    )

    studio_manifest = get_ui_payload(SOURCE, SessionState(), app_path=app_path.as_posix())
    studio_warnings = studio_manifest.get("warnings", [])

    assert _normalize_warnings(cli_warnings) == _normalize_warnings(studio_warnings)
    defaults = studio_manifest.get("state_defaults", {}).get("pages", {}).get("home", {})
    assert defaults.get("chat", {}) == {"messages": [], "citations": [], "memory": [], "thinking": False}
    assert sorted(cli_manifest.get("actions", {}).keys()) == sorted(studio_manifest.get("actions", {}).keys())

    categories = {warn["code"]: warn["category"] for warn in _normalize_warnings(cli_warnings)}
    assert categories["identity.missing"] == "identity"
    assert categories["requires.skipped"] == "permissions"
    assert categories["state.default.missing"] == "state"
    for warn in _normalize_warnings(cli_warnings):
        if warn["code"] in {"identity.missing", "requires.skipped", "state.default.missing"}:
            assert warn["enforced_at"] == "runtime"


def test_studio_actions_payload_surfaces_warnings(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    payload = get_actions_payload(SOURCE, app_path=app_path.as_posix())
    warnings = payload.get("warnings", [])
    codes = {entry.get("code") for entry in warnings}
    assert payload["ok"] is True
    assert "identity.missing" in codes
