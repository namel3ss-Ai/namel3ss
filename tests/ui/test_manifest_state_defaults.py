from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


STATE_WARN_SOURCE = '''spec is "1.0"

record "Metrics":
  value number

page "home":
  table is "Metrics"
  chart from is state.metrics
'''


CHAT_SOURCE = '''spec is "1.0"

flow "send":
  return "ok"

page "home":
  title is "Chat"
  text is "Welcome."
  chat:
    messages from is state.chat.messages
    composer calls flow "send"
    thinking when is state.chat.thinking
    citations from is state.chat.citations
    memory from is state.chat.memory
'''


def test_static_validation_warns_for_missing_state_path() -> None:
    program = lower_ir_program(STATE_WARN_SOURCE)
    warnings = []
    manifest = build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    chart = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "chart")
    assert chart["type"] == "chart"
    assert any(w.code == "state.default.missing" for w in warnings)


def test_declared_defaults_prevent_warnings() -> None:
    program = lower_ir_program(STATE_WARN_SOURCE)
    program.state_defaults = {"metrics": []}
    warnings = []
    manifest = build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    assert not [w for w in warnings if w.code == "state.default.missing"]
    assert manifest["state_defaults"]["app"]["metrics"] == []


def test_chat_defaults_are_injected() -> None:
    program = lower_ir_program(CHAT_SOURCE)
    warnings = []
    manifest = build_manifest(program, state={}, mode=ValidationMode.STATIC, warnings=warnings)
    chat = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "chat")
    children = {child["type"]: child for child in chat["children"]}
    assert children["messages"]["messages"] == []
    assert children["citations"]["citations"] == []
    assert children["memory"]["items"] == []
    assert children["thinking"]["active"] is False
    defaults = manifest["state_defaults"]["pages"]["home"]
    assert defaults.get("chat", {}).get("messages") == []
    assert defaults.get("chat", {}).get("citations") == []
    assert defaults.get("chat", {}).get("memory") == []
    assert defaults.get("chat", {}).get("thinking") is False
    assert warnings
    assert set(w.code for w in warnings) == {"diagnostics.misplaced_debug_content"}
