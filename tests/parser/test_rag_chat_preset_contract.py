from __future__ import annotations

from namel3ss.ir import nodes as ir
from namel3ss.parser.preset_expansion import expand_language_presets
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"
use preset "rag_chat":
  title is "Assistant"

override flow "rag.answer":
  set state.test_observed with:
    message is input.message
    context is input.context
  return input.message
'''


MARKETING_SNIPPET = '''spec is "1.0"
use preset "rag_chat":
  title is "Assistant"

override flow "rag.answer":
  ask ai "gpt-4o-mini" with input:
    query is input.message
    context is input.context
  as answer_text
  return answer_text
'''

SOURCE_TEMPLATE = '''spec is "1.0"
use preset "rag_chat":
  title is "Assistant"
  model is "gpt-4o-mini"
  answer_template is "summary_keypoints_recommendation_with_citations"
'''

SOURCE_TEMPLATE_WITH_FULL_SETTINGS = '''spec is "1.0"
use preset "rag_chat":
  title is "Assistant"
  model is "gpt-4o-mini"
  system is "Custom grounded system prompt."
  temperature is 0.35
  answer_template is "summary_keypoints_recommendation_with_citations"
'''


def test_rag_chat_preset_uses_message_as_canonical_composer_input() -> None:
    program = lower_ir_program(SOURCE)
    contract = program.flow_contracts.get("rag.answer")
    assert contract is not None
    input_names = [field.name for field in contract.signature.inputs]
    assert input_names[0] == "message"
    assert "query" in input_names
    assert "context" in input_names

    page = next(page for page in program.pages if page.name == "Chat")
    chat = next((item for item in _walk_page_items(page.items) if isinstance(item, ir.ChatItem)), None)
    assert isinstance(chat, ir.ChatItem)
    assert chat.attachments is True
    assert chat.composer_attach_upload == "chat_files"

    project_create = next(
        (
            item
            for item in _walk_page_items(page.items)
            if isinstance(item, ir.ButtonItem) and getattr(item, "label", "") == "Create project"
        ),
        None,
    )
    assert isinstance(project_create, ir.ButtonItem)
    assert project_create.flow_name == "rag.create_project"

    chat_upload = next(
        (
            item
            for item in _walk_page_items(page.items)
            if isinstance(item, ir.UploadItem) and getattr(item, "name", "") == "chat_files"
        ),
        None,
    )
    assert isinstance(chat_upload, ir.UploadItem)

    composer = next((item for item in _walk_page_items(page.items) if isinstance(item, ir.ChatComposerItem)), None)
    assert isinstance(composer, ir.ChatComposerItem)
    assert composer.flow_name == "rag.answer"


def test_rag_chat_preset_accepts_marketing_override_input_block() -> None:
    program = lower_ir_program(MARKETING_SNIPPET)
    flow_names = [flow.name for flow in program.flows]
    assert "rag.answer" in flow_names
    assert "rag.ingest" in flow_names


def test_rag_chat_preset_template_generates_internal_answer_ai_and_message_contract() -> None:
    program = lower_ir_program(SOURCE_TEMPLATE)
    contract = program.flow_contracts.get("rag.answer")
    assert contract is not None
    input_names = [field.name for field in contract.signature.inputs]
    assert input_names[0] == "message"

    ai_decl = program.ais.get("__rag_answer_ai")
    assert ai_decl is not None
    assert ai_decl.provider == "openai"
    assert ai_decl.model == "gpt-4o-mini"
    assert ai_decl.memory.short_term == 0
    assert ai_decl.memory.semantic is False
    assert ai_decl.memory.profile is False

    page = next(page for page in program.pages if page.name == "Chat")
    composer = next((item for item in _walk_page_items(page.items) if isinstance(item, ir.ChatComposerItem)), None)
    assert isinstance(composer, ir.ChatComposerItem)
    assert composer.flow_name == "rag.answer"


def test_rag_chat_preset_template_expansion_is_deterministic() -> None:
    first = expand_language_presets(SOURCE_TEMPLATE)
    second = expand_language_presets(SOURCE_TEMPLATE)
    assert first == second
    assert 'ai "__rag_answer_ai":' in first
    assert 'model is "gpt-4o-mini"' in first
    assert 'flow "rag.answer": requires true' in first
    assert 'ask ai "__rag_answer_ai" with structured input from map:' in first


def test_rag_chat_preset_template_generated_blocks_snapshot() -> None:
    expanded = expand_language_presets(SOURCE_TEMPLATE)
    lines = expanded.splitlines()

    ai_start = lines.index('ai "__rag_answer_ai":')
    ai_block = "\n".join(lines[ai_start : ai_start + 8])
    assert ai_block == (
        'ai "__rag_answer_ai":\n'
        '  provider is "openai"\n'
        '  model is "gpt-4o-mini"\n'
        '  system_prompt is "You are a grounded RAG assistant. Return a professional plain-text response with '
        'exactly three sections in this order: Summary, Key Points, Recommendation. Use only grounded evidence '
        'from provided context. Every factual sentence must end with inline citation markers like [1], [2], [3]. '
        'Do not output JSON, YAML, code blocks, file paths, test filenames, or raw context dumps."\n'
        "  memory:\n"
        "    short_term is 0\n"
        "    semantic is false\n"
        "    profile is false"
    )

    override_start = lines.index("  let __rag_template_question is query_text")
    override_block = "\n".join(lines[override_start : override_start + 19])
    assert override_block == (
        "  let __rag_template_question is query_text\n"
        "  let __rag_template_context is context_text\n"
        '  let __rag_answer_text is ""\n'
        "  try:\n"
        '    ask ai "__rag_answer_ai" with structured input from map:\n'
        '      "query" is "Answer this user question with this exact plain-text template and no extra sections:\\n'
        'Summary:\\n<2-3 sentences>\\n\\nKey Points:\\n1. <one sentence>\\n2. <one sentence>\\n3. <one sentence>'
        '\\n\\nRecommendation:\\n<one sentence>\\n\\nRules: use only provided context, keep wording concise and '
        "professional, end factual lines with [1], [2], [3] citations, never output raw context, file paths, URLs, "
        'internal filenames, JSON, YAML, markdown tables, or code blocks.\\n\\nQuestion: " + __rag_template_question\n'
        '      "context" is __rag_template_context\n'
        "    as model_answer\n"
        '    if model_answer is "":\n'
        '      if __rag_template_context is "":\n'
        '        set __rag_answer_text is "No grounded support found in indexed sources for this query."\n'
        "      else:\n"
        '        set __rag_answer_text is "Summary:\\nGrounded evidence was found for this question [1]. A synthesized '
        "response is temporarily unavailable, but the source evidence is indexed and accessible [1].\\n\\nKey Points:"
        '\\n1. Relevant support exists in the indexed sources [1].\\n2. Open View Sources to verify exact snippets '
        "and provenance [1].\\n3. Retry once synthesis is available to receive a fuller narrative [1].\\n\\n"
        'Recommendation:\\nReview the cited evidence now and rerun the same question after provider recovery [1]."\n'
        "    else:\n"
        "      set __rag_answer_text is model_answer\n"
        "  with catch err:\n"
        '    if __rag_template_context is "":\n'
        '      set __rag_answer_text is "No grounded support found in indexed sources for this query."\n'
        "    else:"
    )


def test_rag_chat_preset_accepts_full_template_settings_block() -> None:
    expanded = expand_language_presets(SOURCE_TEMPLATE_WITH_FULL_SETTINGS)
    assert 'model is "gpt-4o-mini"' in expanded
    assert 'system_prompt is "Custom grounded system prompt."' in expanded
    assert 'ask ai "__rag_answer_ai" with structured input from map:' in expanded


def _walk_page_items(items: list[object]) -> list[object]:
    out: list[object] = []
    queue = list(items)
    while queue:
        node = queue.pop(0)
        out.append(node)
        children = getattr(node, "children", None)
        if isinstance(children, list):
            queue.extend(children)
        for attr in ("sidebar", "main"):
            value = getattr(node, attr, None)
            if isinstance(value, list):
                queue.extend(value)
        tabs = getattr(node, "tabs", None)
        if isinstance(tabs, list):
            for tab in tabs:
                tab_children = getattr(tab, "children", None)
                if isinstance(tab_children, list):
                    queue.extend(tab_children)
    return out
