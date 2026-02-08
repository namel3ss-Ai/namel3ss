# UI System

namel3ss UI is semantic and deterministic. You describe intent in `.ai`; the runtime renders it.
There is no CSS or per-component styling. The runtime owns layout, typography, and spacing.

## Mental model
- Pages are structured documents: title, intro text, sections, cards, and rows.
- Pages may also use deterministic layout slots (`header`, `sidebar_left`, `main`, `drawer_right`, `footer`).
- Records power forms, tables, lists, charts, and views.
- Flows power actions; the UI never runs logic on its own.
- UI settings are presets: theme, density, motion, shape, and surface.
- UI also supports deterministic visual themes (`default`, `modern`, `minimal`, `corporate`) and token overrides (colors, font, spacing, radius, shadow).

## Beautiful by default
- Structure is grouped and readable.
- Copy is short and verb-led.
- Tones and icons signal meaning, not decoration.
- The same record looks the same across pages.

## Presets and density
Use the `ui:` block to pick presets. Density controls spacing and grid rhythm.
- `compact` for dense operations
- `comfortable` for general apps
- `spacious` for calm, low-volume screens

See [UI DSL](ui-dsl.md) for the full settings list.

## Warnings surface
Warnings are guidance, not errors. They surface in:
- `/api/ui` and `n3 app.ai ui --json` under `manifest.warnings`
- `/api/actions` and `n3 app.ai actions --json` under `warnings`

Each warning includes `code`, `message`, `fix`, `path`, `line`, `column`, and `category`.

## Deterministic Warning Pipeline
UI warnings are evaluated in a fixed order during manifest build:
1. `layout`
2. `upload`
3. `visibility`
4. `diagnostics`
5. `copy`
6. `story_icon`
7. `consistency`

Each stage uses stable sorting by code and location, so the same `.ai` input produces the same warning list across runs.

## Golden Baselines
Use the baseline suite to lock UI manifest and CSS contracts for representative apps (chat, drawer layouts, conditional sections, uploads):
- `python -m pytest -q tests/ui/test_ui_manifest_baseline.py tests/ui/test_warning_pipeline.py tests/ui/test_layout_primitives.py tests/ui/test_layout_responsive.py`

To refresh committed UI baseline snapshots intentionally:
- `UPDATE_UI_MANIFEST_BASELINES=1 python -m pytest -q tests/ui/test_ui_manifest_baseline.py`

CI runs these tests and fails on snapshot diffs or warning-order regressions.

## Diagnostics vs Product UI
- Keep end-user UI in regular page elements/layout slots.
- Put traces/explain content in `layout.diagnostics` or pages marked `diagnostics is true`.
- Production hides diagnostics by default.
- Studio exposes diagnostics with a `Show Explain` toggle.
- `n3 run --diagnostics <app.ai>` enables diagnostics rendering outside Studio.

## Theming
- Visual theme selection is declarative under `ui:`.
- Theme token overrides are validated and compiled into deterministic CSS with a stable hash.
- Runtime applies compiled CSS and tokens without reload; font loading uses a deterministic URL with fallback to system fonts.

## Templates
Templates live in `src/namel3ss/templates/` and show the full UI system:
- [Operations Dashboard](templates.md#operations-dashboard) - incident queue, table layout, and story tone usage.
- [Onboarding](templates.md#onboarding) - checklist list variant, compose blocks, and calm copy.
- [Support Inbox](templates.md#support-inbox) - queue + compose pairing and action discipline.

## Short checklist
- Title and intro text at the top of each page.
- Group data-heavy elements inside labeled sections or cards.
- Keep rows to three columns or fewer.
- Use one representation and configuration per record across pages.
- Use tones and icons only for meaning.
- Clear warnings with `n3 app.ai check`.

## Related docs
- [UI Quality](ui-quality.md)
- [Layout](ui-layout.md)
- [Copy](ui-copy.md)
- [Icons and Tones](ui-icons-and-tones.md)
- [Consistency](ui-consistency.md)
- [UI DSL](ui-dsl.md)
- [UI See](ui-see.md)
- [Templates](templates.md)
