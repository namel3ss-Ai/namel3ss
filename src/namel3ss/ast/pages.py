from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

from namel3ss.ast.base import Node
from namel3ss.ast.expressions import Expression, Literal, StatePath

if TYPE_CHECKING:  # pragma: no cover - typing-only
    from namel3ss.ast.ui_patterns import PatternArgument


@dataclass
class PageItem(Node):
    visibility: StatePath | None = field(default=None, kw_only=True)
    visibility_rule: "VisibilityRule" | None = field(default=None, kw_only=True)


@dataclass
class VisibilityRule(Node):
    path: StatePath
    value: Literal


@dataclass
class StatusCondition(Node):
    path: StatePath
    kind: str  # equals | empty
    value: Literal | None = None


@dataclass
class StatusCase(Node):
    name: str  # loading | empty | error
    condition: StatusCondition
    items: list["PageItem"]


@dataclass
class StatusBlock(Node):
    cases: list[StatusCase]


@dataclass
class NumberEntry(Node):
    kind: str  # phrase | count
    value: str | None = None
    record_name: str | None = None
    label: str | None = None


@dataclass
class NumberItem(PageItem):
    entries: list[NumberEntry]


@dataclass
class ViewItem(PageItem):
    record_name: str


@dataclass
class ComposeItem(PageItem):
    name: str
    children: list["PageItem"]


@dataclass
class StoryStep(Node):
    title: str
    text: str | None = None
    icon: str | None = None
    image: str | None = None
    image_role: str | None = None
    tone: str | None = None
    requires: str | None = None
    next: str | None = None


@dataclass
class StoryItem(PageItem):
    title: str
    steps: list[StoryStep]


@dataclass
class TitleItem(PageItem):
    value: str


@dataclass
class TextItem(PageItem):
    value: str


@dataclass
class TextInputItem(PageItem):
    name: str
    flow_name: str


@dataclass
class UploadItem(PageItem):
    name: str
    accept: list[str] | None = None
    multiple: bool | None = None


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
    record_name: str | None = None
    source: StatePath | None = None
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
    record_name: str | None = None
    source: StatePath | None = None
    variant: str | None = None
    item: ListItemMapping | None = None
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
class UseUIPackItem(PageItem):
    pack_name: str
    fragment_name: str


@dataclass
class UsePatternItem(PageItem):
    pattern_name: str
    arguments: list["PatternArgument"] | None = None


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
class ChatItem(PageItem):
    children: List["PageItem"]


@dataclass
class TabItem(Node):
    label: str
    children: List["PageItem"]
    visibility: StatePath | None = field(default=None, kw_only=True)
    visibility_rule: VisibilityRule | None = field(default=None, kw_only=True)


@dataclass
class TabsItem(PageItem):
    tabs: List[TabItem]
    default: str | None = None


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
class LinkItem(PageItem):
    label: str
    page_name: str


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
    alt: str | None = None
    role: str | None = None


@dataclass
class PageDecl(Node):
    name: str
    items: List[PageItem]
    requires: Expression | None = None
    purpose: str | None = None
    state_defaults: dict | None = None
    status: StatusBlock | None = None
