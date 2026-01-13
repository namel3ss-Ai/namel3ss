from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ir.model.base import Node
from namel3ss.ir.model.expressions import Expression, StatePath


@dataclass
class Page(Node):
    name: str
    items: List["PageItem"]
    requires: Expression | None = None
    state_defaults: dict | None = None


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
    groups: List["FormGroup"] | None = None
    fields: List["FormFieldConfig"] | None = None


@dataclass
class FormFieldRef(Node):
    name: str


@dataclass
class FormGroup(Node):
    label: str
    fields: List[FormFieldRef]


@dataclass
class FormFieldConfig(Node):
    name: str
    help: str | None = None
    readonly: bool | None = None


@dataclass
class TableColumnDirective(Node):
    kind: str  # include, exclude, label
    name: str
    label: str | None = None


@dataclass
class TableSort(Node):
    by: str
    order: str  # asc, desc


@dataclass
class TablePagination(Node):
    page_size: int


@dataclass
class TableRowAction(Node):
    label: str
    flow_name: str | None = None
    kind: str = "call_flow"
    target: str | None = None


@dataclass
class TableItem(PageItem):
    record_name: str
    columns: List[TableColumnDirective] | None = None
    empty_text: str | None = None
    sort: TableSort | None = None
    pagination: TablePagination | None = None
    selection: str | None = None
    row_actions: List[TableRowAction] | None = None


@dataclass
class ListItemMapping(Node):
    primary: str
    secondary: str | None = None
    meta: str | None = None
    icon: str | None = None


@dataclass
class ListAction(Node):
    label: str
    flow_name: str | None = None
    kind: str = "call_flow"
    target: str | None = None


@dataclass
class ListItem(PageItem):
    record_name: str
    variant: str
    item: ListItemMapping
    empty_text: str | None = None
    selection: str | None = None
    actions: List[ListAction] | None = None


@dataclass
class ChartItem(PageItem):
    record_name: str | None = None
    source: StatePath | None = None
    chart_type: str | None = None
    x: str | None = None
    y: str | None = None
    explain: str | None = None


@dataclass
class ChatMessagesItem(PageItem):
    source: StatePath


@dataclass
class ChatComposerItem(PageItem):
    flow_name: str


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
class ChatItem(PageItem):
    children: List["PageItem"]


@dataclass
class TabItem(Node):
    label: str
    children: List["PageItem"]


@dataclass
class TabsItem(PageItem):
    tabs: List[TabItem]
    default: str


@dataclass
class ModalItem(PageItem):
    label: str
    children: List["PageItem"]


@dataclass
class DrawerItem(PageItem):
    label: str
    children: List["PageItem"]


@dataclass
class ButtonItem(PageItem):
    label: str
    flow_name: str


@dataclass
class SectionItem(PageItem):
    label: str | None
    children: List["PageItem"]


@dataclass
class CardAction(Node):
    label: str
    flow_name: str | None = None
    kind: str = "call_flow"
    target: str | None = None


@dataclass
class CardStat(Node):
    value: Expression
    label: str | None = None


@dataclass
class CardGroupItem(PageItem):
    children: List["PageItem"]


@dataclass
class CardItem(PageItem):
    label: str | None
    children: List["PageItem"]
    stat: CardStat | None = None
    actions: List[CardAction] | None = None


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
    alt: str
