# Layout

What it checks: grouping, nesting depth, row width, action density, and record presentation within pages.

## Warnings
- `layout.flat_page_sprawl` - many top-level elements without grouping.
- `layout.data_ungrouped` - multiple data-heavy elements not inside labeled containers.
- `layout.action_heavy` - too many actions in one container.
- `layout.deep_nesting` - container depth exceeds the limit.
- `layout.grid_sprawl` - too many columns in a row.
- `layout.mixed_record_representation` - a record appears as both table and list.
- `layout.inconsistent_columns` - the same record uses multiple column sets.
- `layout.unlabeled_container` - sections, cards, tabs, drawers, or modals lack labels.

## Fix
Group related content, keep rows small, and keep record layouts consistent.

## Example
```ai
page "home":
  title is "Orders"
  text is "Review incoming orders."
  section "Queue":
    row:
      column:
        card "Open orders":
          table is "Order"
```
