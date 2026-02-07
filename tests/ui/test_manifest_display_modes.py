import hashlib

from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''capabilities:
  uploads

flow "send":
  return "ok"

flow "review":
  return "ok"

page "home":
  button "Send":
    calls flow "send"
  button "Review" debug_only is true:
    calls flow "review"
  chat:
    messages from is state.chat.messages
    thinking when is state.chat.thinking
    citations from is state.chat.citations
    memory from is state.chat.memory

page "devtools":
  debug_only: true
  title is "Debug tools"
'''


STATE = {
    "chat": {
        "messages": [{"role": "user", "content": "Hi"}],
        "thinking": True,
        "citations": [{"title": "Spec", "url": "https://example.com/spec"}],
        "memory": [{"kind": "fact", "text": "x"}],
    }
}


def _all_element_types(manifest: dict) -> set[str]:
    types: set[str] = set()
    for page in manifest.get("pages", []):
        for element in _walk_elements(page.get("elements", [])):
            element_type = element.get("type")
            if isinstance(element_type, str):
                types.add(element_type)
    return types


def _walk_elements(elements: list[dict]):
    for element in elements:
        if not isinstance(element, dict):
            continue
        yield element
        children = element.get("children")
        if isinstance(children, list):
            yield from _walk_elements(children)


def _manifest_hash(manifest: dict) -> str:
    payload = canonical_json_dumps(manifest, pretty=False, drop_run_keys=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_production_mode_filters_debug_only_ui_and_actions():
    program = lower_ir_program(SOURCE)

    studio = build_manifest(program, state=STATE, display_mode="studio")
    production = build_manifest(program, state=STATE, display_mode="production")

    assert studio["mode"] == "studio"
    assert production["mode"] == "production"

    studio_pages = {page["slug"] for page in studio["pages"]}
    production_pages = {page["slug"] for page in production["pages"]}
    assert "devtools" in studio_pages
    assert "devtools" not in production_pages

    studio_types = _all_element_types(studio)
    production_types = _all_element_types(production)
    assert {"thinking", "citations", "memory"}.issubset(studio_types)
    assert {"thinking", "citations", "memory"}.isdisjoint(production_types)

    studio_flow_actions = {action.get("flow") for action in studio["actions"].values() if action.get("type") == "call_flow"}
    production_flow_actions = {action.get("flow") for action in production["actions"].values() if action.get("type") == "call_flow"}
    assert "review" in studio_flow_actions
    assert "review" not in production_flow_actions
    assert "send" in production_flow_actions

    studio_action_types = {action.get("type") for action in studio["actions"].values()}
    production_action_types = {action.get("type") for action in production["actions"].values()}
    assert {"retrieval_run", "ingestion_review", "ingestion_skip", "upload_replace"}.issubset(studio_action_types)
    assert {"retrieval_run", "ingestion_review", "ingestion_skip", "upload_replace"}.isdisjoint(production_action_types)


def test_manifest_mode_filter_is_deterministic_per_mode():
    program = lower_ir_program(SOURCE)

    studio_one = build_manifest(program, state=STATE, display_mode="studio")
    studio_two = build_manifest(program, state=STATE, display_mode="studio")
    production_one = build_manifest(program, state=STATE, display_mode="production")
    production_two = build_manifest(program, state=STATE, display_mode="production")

    assert studio_one == studio_two
    assert production_one == production_two
    assert _manifest_hash(studio_one) == _manifest_hash(studio_two)
    assert _manifest_hash(production_one) == _manifest_hash(production_two)
