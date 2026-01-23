# UI Quality

A practical guide to zero UI warnings.

## Do
- Start each page with a title and one sentence of intro text.
- Group data-heavy elements inside labeled sections or cards.
- Keep rows small (three columns or fewer).
- Use verb-first action labels.
- Use tones and icons only when they add meaning.
- Keep each record consistent across pages.

## Don't
- Stack ungrouped tables, lists, or forms at the top level.
- Nest containers deeply or add too many actions in one card.
- Repeat the same container label in the same page.
- Use a neutral tone with an icon.
- Mix table and list for the same record across pages.

## Structure and spacing
Use the `ui:` block to set density for the whole app.

```ai
ui:
  density is "comfortable"
```

Density controls spacing and rhythm. Choose one density for the app and keep it.

## Copy that stays crisp
Use short labels and plain sentences.

```ai
page "home":
  title is "Operations"
  text is "Monitor incidents and keep owners aligned."
  section "Queue":
    card "Incident list":
      table is "Incident"
  button "Create incident":
    calls flow "create_incident"
```

## Tones and icons
Use tones for signal. Pair non-neutral tones with a matching icon.

```ai
story "Escalation":
  step "Escalate quickly":
    tone is "caution"
    icon is warning
    text is "Escalate high-severity incidents immediately."
```

## Record consistency
Keep one component type and one configuration per record.

```ai
page "active":
  section "Incidents":
    table is "Incident":
      columns:
        include summary
        include status

page "archive":
  section "Incidents":
    table is "Incident":
      columns:
        include summary
        include status
```

## Common warnings
- `layout.flat_page_sprawl` - group top-level items into sections or cards.
- `layout.data_ungrouped` - wrap data-heavy elements in labeled containers.
- `layout.action_heavy` - split large action groups into smaller cards.
- `layout.deep_nesting` - flatten container depth.
- `layout.grid_sprawl` - reduce columns per row.
- `layout.mixed_record_representation` - use one representation for a record.
- `layout.inconsistent_columns` - align table columns for the same record.
- `layout.unlabeled_container` - add labels to sections, cards, tabs, drawers, or modals.
- `copy.missing_page_title` - add a page title.
- `copy.missing_intro_text` - add a short intro text before data-heavy elements.
- `copy.unlabeled_container` - label sections, cards, tabs, drawers, or modals.
- `copy.duplicate_container_label` - make container labels unique within a page.
- `copy.text_too_long` - split long text into shorter blocks.
- `copy.action_label` - use a short verb-first label.
- `story.tone_missing_icon` - add a matching icon or remove the tone.
- `story.icon_tone_mismatch` - use a tone-aligned icon.
- `story.tone_overuse` - keep most steps neutral.
- `icon.misuse` - avoid icons on neutral steps.
- `icon.inconsistent_semantics` - use one icon per tone across the app.
- `icon.overuse` - reserve icons for key steps.
- `consistency.record_component_type` - use one component type per record.
- `consistency.record_configuration` - align table/list/form/chart settings.
- `consistency.chart_pairing` - pair charts with the same source type.

## Where warnings appear
- `/api/ui` and `n3 app.ai ui --json` under `manifest.warnings`
- `/api/actions` and `n3 app.ai actions --json` under `warnings`
