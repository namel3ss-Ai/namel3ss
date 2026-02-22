from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from namel3ss.ir.model.base import Node
from namel3ss.ir.model.expressions import Expression, Literal, StatePath
from namel3ss.ir.model.ui_theme import ThemeTokenOverrides, ThemeTokens


@dataclass
class Page(Node):
    name: str
    items: List["PageItem"]
    layout: "PageLayout | None" = None
    requires: Expression | None = None
    visibility: Expression | None = field(default=None, kw_only=True)
    visibility_rule: "VisibilityRule | VisibilityExpressionRule" | None = field(default=None, kw_only=True)
    purpose: str | None = None
    state_defaults: dict | None = None
    status: "StatusBlock" | None = None
    debug_only: bool | str | None = None
    diagnostics: bool | None = None
    theme_tokens: ThemeTokens | None = None
    ui_theme_overrides: ThemeTokens | None = None

@dataclass
class PageLayout(Node):
    header: list["PageItem"]
    sidebar_left: list["PageItem"]
    main: list["PageItem"]
    drawer_right: list["PageItem"]
    footer: list["PageItem"]
    diagnostics: list["PageItem"] = field(default_factory=list)
    sidebar_width: str | None = None
    drawer_width: str | None = None
    panel_height: str | None = None
    resizable_panels: bool | None = None


@dataclass
class PageItem(Node):
    visibility: Expression | None = field(default=None, kw_only=True)
    visibility_rule: "VisibilityRule | VisibilityExpressionRule" | None = field(default=None, kw_only=True)
    show_when: Expression | None = field(default=None, kw_only=True)
    debug_only: bool | str | None = field(default=None, kw_only=True)
    theme_overrides: ThemeTokenOverrides | None = field(default=None, kw_only=True)


@dataclass
class VisibilityRule(Node):
    path: StatePath
    value: Literal


@dataclass
class VisibilityExpressionRule(Node):
    expression: Expression


@dataclass
class ActionAvailabilityRule(Node):
    path: StatePath
    value: Literal


@dataclass
class ActivePageRule(Node):
    page_name: str
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
    availability_rule: ActionAvailabilityRule | None = field(default=None, kw_only=True)


@dataclass
class SliderItem(PageItem):
    label: str
    min_value: float
    max_value: float
    step: float
    value: StatePath
    flow_name: str
    help_text: str | None = None


@dataclass
class TooltipItem(PageItem):
    text: str
    anchor_label: str
    collapsed_by_default: bool = True


@dataclass
class UploadItem(PageItem):
    name: str
    accept: list[str]
    multiple: bool
    required: bool = False
    label: str = "Upload"
    preview: bool = False


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
    availability_rule: ActionAvailabilityRule | None = field(default=None, kw_only=True)


@dataclass
class TableItem(PageItem):
    record_name: str | None = None
    source: StatePath | None = None
    columns: List[TableColumnDirective] | None = None
    empty_text: str | None = None
    empty_state_hidden: bool = False
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
    icon_color: str | None = None


@dataclass
class ListAction(Node):
    label: str
    flow_name: str | None = None
    kind: str = "call_flow"
    target: str | None = None
    ui_behavior: str | None = None
    availability_rule: ActionAvailabilityRule | None = field(default=None, kw_only=True)


@dataclass
class ListItem(PageItem):
    variant: str
    item: ListItemMapping
    record_name: str | None = None
    source: StatePath | None = None
    empty_text: str | None = None
    empty_state_hidden: bool = False
    selection: str | None = None
    actions: List[ListAction] | None = None
    group_by: str | None = None
    group_label: str | None = None


@dataclass
class ChartItem(PageItem):
    record_name: str | None = None
    source: StatePath | None = None
    chart_type: str | None = None
    x: str | None = None
    y: str | None = None
    explain: str | None = None


from namel3ss.ir.model.page_chat_items import (  # noqa: E402
    ChatCitationsItem,
    ChatComposerField,
    ChatComposerItem,
    ChatItem,
    ChatMemoryItem,
    ChatMessagesItem,
    ChatThinkingItem,
    CitationChipsItem,
    ScopeSelectorItem,
    SourcePreviewItem,
    TrustIndicatorItem,
)


@dataclass
class CustomComponentProp(Node):
    name: str
    value: object


@dataclass
class CustomComponentItem(PageItem):
    component_name: str
    properties: list[CustomComponentProp]
    plugin_name: str | None = None


@dataclass
class TabItem(Node):
    label: str
    children: List["PageItem"]
    visibility: Expression | None = field(default=None, kw_only=True)
    visibility_rule: VisibilityRule | VisibilityExpressionRule | None = field(default=None, kw_only=True)
    show_when: Expression | None = field(default=None, kw_only=True)


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
    flow_name: str | None = None
    action_kind: str = "call_flow"
    target: str | None = None
    icon: str | None = None
    availability_rule: ActionAvailabilityRule | None = field(default=None, kw_only=True)


@dataclass
class LinkItem(PageItem):
    label: str
    page_name: str


@dataclass
class SectionItem(PageItem):
    label: str | None
    children: List["PageItem"]
    columns: list[int] | None = None


@dataclass
class CardAction(Node):
    label: str
    flow_name: str | None = None
    kind: str = "call_flow"
    target: str | None = None
    availability_rule: ActionAvailabilityRule | None = field(default=None, kw_only=True)


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
class GridItem(PageItem):
    columns: list[int]
    children: List["PageItem"]


@dataclass
class DividerItem(PageItem):
    pass


@dataclass
class ImageItem(PageItem):
    src: str
    alt: str
    role: str | None = None


@dataclass
class LoadingItem(PageItem):
    variant: str = "spinner"


@dataclass
class BadgeItem(PageItem):
    source: StatePath
    style: str = "neutral"


@dataclass
class SnackbarItem(PageItem):
    message: str
    duration: int = 3000


@dataclass
class IconItem(PageItem):
    name: str
    size: str = "medium"
    role: str = "decorative"
    label: str | None = None


@dataclass
class LightboxItem(PageItem):
    images: list[str] | None = None
    start_index: int = 0


@dataclass
class ThemeSettingsPageItem(PageItem):
    pass
