from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ir.model.base import Node


@dataclass
class Page(Node):
    name: str
    items: List["PageItem"]


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
