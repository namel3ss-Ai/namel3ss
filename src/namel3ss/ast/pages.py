from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast.base import Node
from namel3ss.ast.expressions import Expression


@dataclass
class PageItem(Node):
    pass


@dataclass
class TitleItem(PageItem):
    value: str


@dataclass
class TextItem(PageItem):
    value: str


@dataclass
class FormItem(PageItem):
    record_name: str


@dataclass
class TableItem(PageItem):
    record_name: str


@dataclass
class ButtonItem(PageItem):
    label: str
    flow_name: str


@dataclass
class SectionItem(PageItem):
    label: str | None
    children: List["PageItem"]


@dataclass
class CardItem(PageItem):
    label: str | None
    children: List["PageItem"]


@dataclass
class RowItem(PageItem):
    children: List["PageItem"]


@dataclass
class ColumnItem(PageItem):
    children: List["PageItem"]


@dataclass
class DividerItem(PageItem):
    pass


@dataclass
class ImageItem(PageItem):
    src: str
    alt: str | None = None


@dataclass
class PageDecl(Node):
    name: str
    items: List[PageItem]
    requires: Expression | None = None
