# Consistency

What it checks: stable record representation across pages.

## Warnings
- `consistency.record_component_type` - the same record uses different component types across pages.
- `consistency.record_configuration` - tables, lists, forms, or charts use different configurations across pages.
- `consistency.chart_pairing` - charts for the same record pair with different source types.

## Fix
Pick one component type and keep its configuration aligned across pages.

## Example
```ai
page "active":
  section "Incidents":
    table is "Incident":
      columns:
        include summary
        include status

page "history":
  section "Incidents":
    table is "Incident":
      columns:
        include summary
        include status
```
