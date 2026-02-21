from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Final

from namel3ss.parser.presets.rag_chat_core import build_rag_chat_core_lines
from namel3ss.parser.presets.rag_chat_page import (
    build_rag_chat_pre_override_lines,
    build_rag_chat_suffix_lines,
)

RAG_CHAT_TEMPLATE_PLAIN_CONCISE: Final[str] = "plain_concise"
RAG_CHAT_TEMPLATE_SUMMARY_KEYPOINTS_RECOMMENDATION_WITH_CITATIONS: Final[str] = (
    "summary_keypoints_recommendation_with_citations"
)
SUPPORTED_RAG_CHAT_ANSWER_TEMPLATES: Final[tuple[str, ...]] = (
    RAG_CHAT_TEMPLATE_PLAIN_CONCISE,
    RAG_CHAT_TEMPLATE_SUMMARY_KEYPOINTS_RECOMMENDATION_WITH_CITATIONS,
)
DEFAULT_RAG_CHAT_MODEL: Final[str] = "gpt-4o-mini"
DEFAULT_RAG_CHAT_TEMPERATURE: Final[float] = 0.2
DEFAULT_RAG_CHAT_SYSTEM_PROMPT: Final[str] = (
    "You are a grounded RAG assistant. Return a professional plain-text response with exactly three sections "
    "in this order: Summary, Key Points, Recommendation. Use only grounded evidence from provided context. "
    "Every factual sentence must end with inline citation markers like [1], [2], [3]. "
    "Do not output JSON, YAML, code blocks, file paths, test filenames, or raw context dumps."
)
RAG_CHAT_INTERNAL_ANSWER_AI_NAME: Final[str] = "__rag_answer_ai"
NO_GROUNDED_SUPPORT_MESSAGE: Final[str] = "No grounded support found in indexed sources for this query."
SUMMARY_TEMPLATE_QUERY_PROMPT: Final[str] = (
    "Answer this user question with this exact plain-text template and no extra sections:\n"
    "Summary:\n"
    "<2-3 sentences>\n\n"
    "Key Points:\n"
    "1. <one sentence>\n"
    "2. <one sentence>\n"
    "3. <one sentence>\n\n"
    "Recommendation:\n"
    "<one sentence>\n\n"
    "Rules: use only provided context, keep wording concise and professional, end factual lines with [1], [2], [3] "
    "citations, never output raw context, file paths, URLs, internal filenames, JSON, YAML, markdown tables, or "
    "code blocks.\n\n"
    "Question: "
)
SUMMARY_TEMPLATE_EMPTY_OUTPUT_FALLBACK: Final[str] = (
    "Summary:\n"
    "Grounded evidence was found for this question [1]. A synthesized response is temporarily unavailable, but the "
    "source evidence is indexed and accessible [1].\n\n"
    "Key Points:\n"
    "1. Relevant support exists in the indexed sources [1].\n"
    "2. Open View Sources to verify exact snippets and provenance [1].\n"
    "3. Retry once synthesis is available to receive a fuller narrative [1].\n\n"
    "Recommendation:\n"
    "Review the cited evidence now and rerun the same question after provider recovery [1]."
)
SUMMARY_TEMPLATE_PROVIDER_ERROR_FALLBACK: Final[str] = (
    "Summary:\n"
    "Grounded evidence was found for this question [1]. AI synthesis is currently unavailable in this runtime [1].\n\n"
    "Key Points:\n"
    "1. The indexed context contains supporting information [1].\n"
    "2. View Sources remains available for direct evidence review [1].\n"
    "3. Provider credentials are required for synthesized answers [1].\n\n"
    "Recommendation:\n"
    "Set NAMEL3SS_OPENAI_API_KEY, rerun the app, and ask again for a fully composed response [1]."
)


@dataclass(frozen=True)
class RagChatPresetConfig:
    title: str = "Assistant"
    accept: str | None = None
    model: str = DEFAULT_RAG_CHAT_MODEL
    system: str | None = None
    temperature: float = DEFAULT_RAG_CHAT_TEMPERATURE
    answer_template: str = RAG_CHAT_TEMPLATE_PLAIN_CONCISE


def render_rag_chat_source(
    *,
    spec_line: str,
    config: RagChatPresetConfig,
    override_body: list[str] | None,
) -> str:
    title = _escape_string(config.title)
    accept = _escape_string(config.accept or "application/pdf,text/plain")
    active_override = override_body or _default_override_body(config)
    generated_ai_blocks = _build_generated_ai_blocks(config=config, override_body=override_body)
    generated_ai_names = {entry[0] for entry in generated_ai_blocks}
    ai_names = _collect_ai_names(active_override)
    lines: list[str] = [
        spec_line,
        "",
        "capabilities:",
        "  uploads",
        "  http",
        "  streaming",
        "  `ui`.theming",
        "  ui_navigation",
        "  ui_state",
        "",
        "ui_state:",
        "  session:",
        "    preview_source is text",
        "    citation_highlight_color is text",
        "    active_project_id is text",
        "",
        "ui:",
        '  preset is "clarity"',
        '  theme is "light"',
        '  accent color is "blue"',
        '  density is "comfortable"',
        '  motion is "none"',
        '  shape is "soft"',
        '  surface is "flat"',
        '  primary color is "#0A66C2"',
        '  secondary color is "#E6ECF5"',
        '  background color is "#FAFBFD"',
        '  foreground color is "#111827"',
        '  font family is "IBM Plex Sans, Segoe UI, sans-serif"',
        "  spacing scale is 1.0",
        "  border radius is 6",
        "  shadow level is 0",
        "",
    ]
    for _, block_lines in generated_ai_blocks:
        lines.extend(block_lines)
    for ai_name in ai_names:
        if ai_name in generated_ai_names:
            continue
        escaped = _escape_string(ai_name)
        lines.extend(
            [
                f'ai "{escaped}":',
                f'  model is "{escaped}"',
                "",
            ]
        )
    lines.extend(build_rag_chat_core_lines())
    lines.extend(build_rag_chat_pre_override_lines())
    lines.extend(_indent_lines(active_override))
    lines.extend(build_rag_chat_suffix_lines(title=title, accept=accept))
    return "\n".join(lines).rstrip() + "\n"


def _build_generated_ai_blocks(
    *,
    config: RagChatPresetConfig,
    override_body: list[str] | None,
) -> list[tuple[str, list[str]]]:
    if override_body is not None:
        return []
    if config.answer_template != RAG_CHAT_TEMPLATE_SUMMARY_KEYPOINTS_RECOMMENDATION_WITH_CITATIONS:
        return []
    model = _escape_string(config.model or DEFAULT_RAG_CHAT_MODEL)
    system_prompt = _escape_string(config.system or DEFAULT_RAG_CHAT_SYSTEM_PROMPT)
    return [
        (
            RAG_CHAT_INTERNAL_ANSWER_AI_NAME,
            [
                f'ai "{RAG_CHAT_INTERNAL_ANSWER_AI_NAME}":',
                '  provider is "openai"',
                f'  model is "{model}"',
                f'  system_prompt is "{system_prompt}"',
                "  memory:",
                "    short_term is 0",
                "    semantic is false",
                "    profile is false",
                "",
            ],
        )
    ]


def _default_override_body(config: RagChatPresetConfig) -> list[str]:
    if config.answer_template == RAG_CHAT_TEMPLATE_SUMMARY_KEYPOINTS_RECOMMENDATION_WITH_CITATIONS:
        return _summary_template_override_body()
    return [
        "set __rag_answer_text is context_text",
    ]


def _summary_template_override_body() -> list[str]:
    prompt = _escape_string(SUMMARY_TEMPLATE_QUERY_PROMPT)
    no_support = _escape_string(NO_GROUNDED_SUPPORT_MESSAGE)
    empty_output_fallback = _escape_string(SUMMARY_TEMPLATE_EMPTY_OUTPUT_FALLBACK)
    provider_error_fallback = _escape_string(SUMMARY_TEMPLATE_PROVIDER_ERROR_FALLBACK)
    return [
        "let __rag_template_question is query_text",
        "let __rag_template_context is context_text",
        'let __rag_answer_text is ""',
        "try:",
        f'  ask ai "{RAG_CHAT_INTERNAL_ANSWER_AI_NAME}" with structured input from map:',
        f'    "query" is "{prompt}" + __rag_template_question',
        '    "context" is __rag_template_context',
        "  as model_answer",
        '  if model_answer is "":',
        '    if __rag_template_context is "":',
        f'      set __rag_answer_text is "{no_support}"',
        "    else:",
        f'      set __rag_answer_text is "{empty_output_fallback}"',
        "  else:",
        "    set __rag_answer_text is model_answer",
        "with catch err:",
        '  if __rag_template_context is "":',
        f'    set __rag_answer_text is "{no_support}"',
        "  else:",
        f'    set __rag_answer_text is "{provider_error_fallback}"',
    ]


def _collect_ai_names(lines: list[str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for line in lines:
        match = re.search(r'ask\s+ai\s+"([^"]+)"', line)
        if not match:
            continue
        name = str(match.group(1) or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _indent_lines(lines: list[str], *, prefix: str = "  ") -> list[str]:
    return [(prefix + line) if line else "" for line in lines]


def _escape_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")


__all__ = [
    "RagChatPresetConfig",
    "render_rag_chat_source",
    "SUPPORTED_RAG_CHAT_ANSWER_TEMPLATES",
    "RAG_CHAT_TEMPLATE_PLAIN_CONCISE",
    "RAG_CHAT_TEMPLATE_SUMMARY_KEYPOINTS_RECOMMENDATION_WITH_CITATIONS",
    "DEFAULT_RAG_CHAT_MODEL",
    "DEFAULT_RAG_CHAT_TEMPERATURE",
    "DEFAULT_RAG_CHAT_SYSTEM_PROMPT",
]
