from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

from namel3ss.ast.base import Node
from namel3ss.ast.expressions import Expression, Literal, StatePath
from namel3ss.ast.ui_theme import ThemeTokenOverrides, ThemeTokens

if TYPE_CHECKING:  # pragma: no cover - typing-only
    from namel3ss.ast.ui_patterns import PatternArgument

@dataclass
class PageItem(Node):
    visibility: Expression | "PatternParamRef" | None = field(default=None, kw_only=True)
    visibility_rule: "VisibilityRule | VisibilityExpressionRule" | None = field(default=None, kw_only=True)
    show_when: Expression | "PatternParamRef" | None = field(default=None, kw_only=True)
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
    accept: list[str] | None = None
    multiple: bool | None = None
    required: bool | None = None
    label: str | None = None
    preview: bool | None = None

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
    record_name: str | None = None
    source: StatePath | None = None
    variant: str | None = None
    item: ListItemMapping | None = None
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
    visibility: Expression | "PatternParamRef" | None = field(default=None, kw_only=True)
    visibility_rule: VisibilityRule | VisibilityExpressionRule | None = field(default=None, kw_only=True)
    show_when: Expression | "PatternParamRef" | None = field(default=None, kw_only=True)

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
    alt: str | None = None
    role: str | None = None

@dataclass
class LoadingItem(PageItem):
    variant: str = "spinner"

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
    images: list[str]
    start_index: int = 0

@dataclass
class ThemeSettingsPageItem(PageItem):
    pass

@dataclass
class PageLayout(Node):
    header: list["PageItem"] = field(default_factory=list)
    sidebar_left: list["PageItem"] = field(default_factory=list)
    main: list["PageItem"] = field(default_factory=list)
    drawer_right: list["PageItem"] = field(default_factory=list)
    footer: list["PageItem"] = field(default_factory=list)
    diagnostics: list["PageItem"] = field(default_factory=list)
    sidebar_width: str | None = None
    drawer_width: str | None = None
    panel_height: str | None = None
    resizable_panels: bool | None = None

@dataclass
class PageDecl(Node):
    name: str
    items: List[PageItem]
    layout: PageLayout | None = None
    requires: Expression | None = None
    visibility: Expression | "PatternParamRef" | None = None
    visibility_rule: VisibilityRule | VisibilityExpressionRule | None = None
    purpose: str | None = None
    state_defaults: dict | None = None
    debug_only: bool | str | None = None
    diagnostics: bool | None = None
    status: StatusBlock | None = None
    theme_tokens: ThemeTokens | None = None
