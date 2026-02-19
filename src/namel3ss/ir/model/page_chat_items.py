from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from namel3ss.ir.model.base import Node
from namel3ss.ir.model.expressions import Literal, StatePath
from namel3ss.ir.model.pages import PageItem


@dataclass
class ChatMessagesItem(PageItem):
    source: StatePath


@dataclass
class ChatComposerField(Node):
    name: str
    type_name: str
    type_was_alias: bool = False
    raw_type_name: str | None = None
    type_line: int | None = None
    type_column: int | None = None


@dataclass
class ChatComposerItem(PageItem):
    flow_name: str
    fields: list[ChatComposerField] = field(default_factory=list)


@dataclass
class ChatThinkingItem(PageItem):
    when: StatePath


@dataclass
class ChatCitationsItem(PageItem):
    source: StatePath


@dataclass
class ChatMemoryItem(PageItem):
    source: StatePath
    lane: str | None = None


@dataclass
class CitationChipsItem(PageItem):
    source: StatePath


@dataclass
class SourcePreviewItem(PageItem):
    source: StatePath | Literal


@dataclass
class TrustIndicatorItem(PageItem):
    source: StatePath


@dataclass
class ScopeSelectorItem(PageItem):
    options_source: StatePath
    active: StatePath


@dataclass
class ChatItem(PageItem):
    children: List["PageItem"]
    style: str = "bubbles"
    show_avatars: bool = False
    group_messages: bool = True
    actions: list[str] = field(default_factory=list)
    streaming: bool = False
    attachments: bool = False
    composer_placeholder: str | None = None
    composer_send_style: str = "icon"
    composer_attach_upload: str | None = None


__all__ = [
    "ChatMessagesItem",
    "ChatComposerField",
    "ChatComposerItem",
    "ChatThinkingItem",
    "ChatCitationsItem",
    "ChatMemoryItem",
    "CitationChipsItem",
    "SourcePreviewItem",
    "TrustIndicatorItem",
    "ScopeSelectorItem",
    "ChatItem",
]
