from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from namel3ss.page_layout import PAGE_LAYOUT_SLOT_ORDER
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


BASELINE_FIXTURES_DIR = Path("tests/fixtures/ui_manifest_baselines")
CSS_PATHS = (
    Path("src/namel3ss/studio/web/studio_ui.css"),
    Path("src/namel3ss/studio/web/styles.css"),
)

TYPE_CSS_SELECTORS: dict[str, tuple[str, ...]] = {
    "card": (".ui-card", ".ui-card-title", ".ui-card-actions"),
    "chat": (".ui-chat", ".ui-chat-messages", ".ui-chat-composer"),
    "citation_chips": (".ui-citation-chips", ".ui-citation-chip"),
    "citations": (".ui-chat-citations", ".ui-chat-citation", ".ui-chat-citation-actions"),
    "column": (".ui-column",),
    "drawer": (".ui-overlay", ".ui-overlay.ui-drawer", ".ui-overlay-panel", ".ui-overlay-body"),
    "form": (".ui-form", ".ui-form-field", ".ui-form .errors"),
    "ingestion_status": (".ui-ingestion-status", ".ui-ingestion-status-reason", ".ui-ingestion-status-code"),
    "retrieval_explain": (".ui-retrieval-explain", ".ui-retrieval-explain-row", ".ui-retrieval-explain-trust-badge"),
    "runtime_error": (".ui-runtime-error", ".ui-runtime-error-badge", ".ui-runtime-error-message"),
    "list": (".ui-list", ".ui-list-item"),
    "memory": (".ui-chat-memory", ".ui-chat-memory-item"),
    "messages": (".ui-chat-message",),
    "page_layout": (
        ".n3-layout-root",
        ".n3-layout-header",
        ".n3-layout-body",
        ".n3-layout-sidebar",
        ".n3-layout-main",
        ".n3-layout-drawer",
        ".n3-layout-footer",
    ),
    "modal": (".ui-overlay", ".ui-overlay-panel", ".ui-overlay-body"),
    "row": (".ui-row",),
    "scope_selector": (".ui-scope-selector", ".ui-scope-option"),
    "section": (".ui-section", ".ui-section-title"),
    "source_preview": (".ui-source-preview", ".ui-source-preview-title"),
    "table": (".ui-table",),
    "tabs": (".ui-tabs", ".ui-tabs-header"),
    "thinking": (".ui-chat-thinking",),
    "trust_indicator": (".ui-trust-indicator",),
    "upload": (".ui-upload", ".ui-upload-file-item", ".ui-upload-status"),
}

BASE_SELECTORS = (".btn", ".btn.small", ".topbar")


@dataclass(frozen=True)
class UIBaselineCase:
    name: str
    source: str
    state: dict
    expected_warning_codes: tuple[str, ...]
    required_element_types: tuple[str, ...]
    required_action_types: tuple[str, ...]


def baseline_cases() -> tuple[UIBaselineCase, ...]:
    return (
        UIBaselineCase(
            name="chat_page",
            source='''spec is "1.0"

flow "send_message":
  return "ok"

page "chat":
  title is "Support chat"
  text is "Talk to the assistant."
  section "Conversation":
    chat:
      messages from is state.chat.messages
      composer calls flow "send_message"
      thinking when is state.chat.thinking
      citations from is state.chat.citations
      memory from is state.chat.memory
''',
            state={
                "chat": {
                    "messages": [{"role": "user", "content": "Hi"}],
                    "thinking": False,
                    "citations": [{"title": "Spec", "url": "https://example.com/spec"}],
                    "memory": [{"kind": "fact", "text": "Account active"}],
                }
            },
            expected_warning_codes=("diagnostics.misplaced_debug_content",),
            required_element_types=("chat", "messages", "composer", "citations", "memory"),
            required_action_types=("call_flow",),
        ),
        UIBaselineCase(
            name="drawer_layout",
            source='''spec is "1.0"

page "ops":
  title is "Operations"
  text is "Track queue and open details."
  section "Queue":
    row:
      column:
        card "Summary":
          text is "Incidents are stable."
      column:
        card "Actions":
          actions:
            action "Open details":
              opens drawer "Details"
  drawer "Details":
    text is "Drawer content"
''',
            state={},
            expected_warning_codes=(),
            required_element_types=("row", "column", "drawer", "card"),
            required_action_types=("open_drawer",),
        ),
        UIBaselineCase(
            name="slot_layout",
            source='''spec is "1.0"

flow "send":
  return "ok"

page "support":
  layout:
    header:
      title is "Support Inbox"
      text is "Review active conversations."
    sidebar_left:
      section "Folders":
        text is "Open"
    main:
      section "Messages":
        chat:
          messages from is state.messages
          composer calls flow "send"
    drawer_right:
      section "Details":
        text is "Select a message."
    footer:
      text is "Powered by Namel3ss"
''',
            state={
                "messages": [{"role": "user", "content": "Hello"}],
            },
            expected_warning_codes=(),
            required_element_types=("page_layout", "section", "chat", "messages", "composer"),
            required_action_types=("call_flow",),
        ),
        UIBaselineCase(
            name="conditional_upload",
            source='''spec is "1.0"

capabilities:
  uploads

record "Receipt":
  name text
  amount number

flow "submit_receipt":
  let files is state.uploads.receipt
  return files

page "intake":
  title is "Receipt intake"
  text is "Upload receipts and review extracted rows."
  section "Upload":
    upload receipt:
      accept is "pdf", "png"
      multiple is true
    button "Submit receipt":
      calls flow "submit_receipt"
  section "Review" visibility is state.show_review:
    table is "Receipt"
''',
            state={"show_review": False},
            expected_warning_codes=(),
            required_element_types=("upload", "table", "section"),
            required_action_types=("upload_select", "ingestion_run", "call_flow"),
        ),
        UIBaselineCase(
            name="warning_misconfigured",
            source='''spec is "1.0"

record "Order":
  name text

flow "execute":
  return "ok"

page "home":
  table is "Order"
  section:
    text is "Missing label"
  button "More details about the report status and metrics":
    calls flow "execute"
''',
            state={},
            expected_warning_codes=(
                "copy.action_label",
                "copy.missing_intro_text",
                "copy.missing_page_title",
                "copy.unlabeled_container",
                "layout.unlabeled_container",
            ),
            required_element_types=("table", "section", "button"),
            required_action_types=("call_flow",),
        ),
        UIBaselineCase(
            name="rag_page",
            source='''spec is "1.0"

flow "send":
  return "ok"

page "rag":
  layout:
    header:
      title is "Ask the Docs"
    sidebar_left:
      scope_selector from state.documents active in state.active_docs
    main:
      section "Answer":
        text is "Grounded answer"
        citations from state.answer.citations
        trust_indicator from state.answer.trusted
      chat:
        messages from is state.chat.messages
        composer calls flow "send"
    drawer_right:
      source_preview from state.preview
''',
            state={
                "documents": [
                    {"id": "policy", "name": "Policy docs"},
                    {"id": "handbook", "name": "Handbook"},
                ],
                "active_docs": ["policy"],
                "answer": {
                    "citations": [{"title": "Policy", "source_id": "doc-policy"}],
                    "trusted": True,
                },
                "preview": {"title": "Policy", "source_id": "doc-policy", "snippet": "Policy source"},
                "chat": {"messages": [{"role": "assistant", "content": "Grounded answer"}]},
            },
            expected_warning_codes=(),
            required_element_types=("scope_selector", "citation_chips", "trust_indicator", "source_preview", "chat"),
            required_action_types=("scope_select", "call_flow"),
        ),
    )


def build_case_snapshot(case: UIBaselineCase) -> dict:
    program = lower_ir_program(case.source)
    warnings: list = []
    manifest = build_manifest(
        program,
        state=dict(case.state),
        store=None,
        mode=ValidationMode.STATIC,
        warnings=warnings,
    )
    warning_payloads = [warning.to_dict() for warning in warnings]
    if warning_payloads:
        manifest["warnings"] = warning_payloads
    element_types = sorted(_collect_element_types(manifest))
    action_types = sorted(_collect_action_types(manifest))
    warning_codes = sorted(entry.get("code") for entry in warning_payloads if isinstance(entry.get("code"), str))
    css_contract = build_css_contract(element_types)
    return {
        "manifest": manifest,
        "summary": {
            "element_types": element_types,
            "action_types": action_types,
            "warning_codes": warning_codes,
        },
        "css_contract": css_contract,
    }


def build_css_contract(element_types: list[str]) -> dict:
    rules = _read_css_rules()
    selectors = set(BASE_SELECTORS)
    for element_type in element_types:
        selectors.update(TYPE_CSS_SELECTORS.get(element_type, ()))
    selector_rules = {selector: sorted(rules.get(selector, [])) for selector in sorted(selectors)}
    sticky_topbar = any("position: sticky" in rule for rule in selector_rules.get(".topbar", []))
    return {
        "selectors": selector_rules,
        "sticky_topbar": sticky_topbar,
    }


def _collect_element_types(manifest: dict) -> set[str]:
    types: set[str] = set()
    pages = manifest.get("pages") if isinstance(manifest, dict) else None
    if not isinstance(pages, list):
        return types
    for page in pages:
        if not isinstance(page, dict):
            continue
        layout = page.get("layout")
        if isinstance(layout, dict):
            types.add("page_layout")
            for slot_name in PAGE_LAYOUT_SLOT_ORDER:
                for element in _walk_elements(layout.get(slot_name)):
                    element_type = element.get("type")
                    if isinstance(element_type, str):
                        types.add(element_type)
            continue
        for element in _walk_elements(page.get("elements")):
            element_type = element.get("type")
            if isinstance(element_type, str):
                types.add(element_type)
    return types


def _walk_elements(elements: object):
    if not isinstance(elements, list):
        return
    for element in elements:
        if not isinstance(element, dict):
            continue
        yield element
        yield from _walk_elements(element.get("children"))


def _collect_action_types(manifest: dict) -> set[str]:
    types: set[str] = set()
    actions = manifest.get("actions") if isinstance(manifest, dict) else None
    if not isinstance(actions, dict):
        return types
    for action in actions.values():
        if not isinstance(action, dict):
            continue
        action_type = action.get("type")
        if isinstance(action_type, str):
            types.add(action_type)
    return types


def _read_css_rules() -> dict[str, list[str]]:
    rules: dict[str, list[str]] = {}
    for path in CSS_PATHS:
        text = path.read_text(encoding="utf-8")
        for selector_group, body in re.findall(r"([^{}]+)\{([^{}]+)\}", text, flags=re.MULTILINE):
            normalized_body = _normalize_css_body(body)
            if not normalized_body:
                continue
            for selector in selector_group.split(","):
                key = selector.strip()
                if not key or key.startswith("@"):
                    continue
                rules.setdefault(key, []).append(normalized_body)
    return rules


def _normalize_css_body(body: str) -> str:
    declarations = [part.strip() for part in body.split(";") if part.strip()]
    compact = [re.sub(r"\s+", " ", part) for part in declarations]
    return "; ".join(compact)


__all__ = [
    "BASELINE_FIXTURES_DIR",
    "UIBaselineCase",
    "baseline_cases",
    "build_case_snapshot",
]
