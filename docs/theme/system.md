# Theme System

## Overview

Namel3ss theming is deterministic and compile-time driven. Theme values are converted to manifest tokens and CSS variables that runtime and Studio consume consistently.

This Phase 4 system adds:

- Base themes: `default`, `dark`, `high_contrast`
- Deterministic token schema metadata (`theme.token_schema`)
- Theme configuration payload (`theme.config`) in manifest output
- CSS variable usage across layout/chat/drawer/empty-state styles

## Capability

No new capability is required.

- Existing pages continue to work with default tokens.
- Existing UI theme features remain backward compatible.
- Optional explicit `ui_theme_config` on IR program input enables base-theme selection plus overrides.

## Token Contract

Token names are stable and ordered:

- `primary_color`
- `secondary_color`
- `background_color`
- `foreground_color`
- `font_family`
- `font_size_base`
- `font_weight`
- `spacing_scale`
- `border_radius`
- `shadow_level`

`theme.token_schema` includes deterministic metadata:

- `type`
- `category`
- `description`

## Theme Configuration Contract

Manifest exposes:

- `theme.base_theme`
- `theme.themes_available`
- `theme.config.base_theme`
- `theme.config.overrides`

Example JSON:

```json
{
  "base_theme": "high_contrast",
  "overrides": {
    "primary_color": "#FFAA00",
    "spacing_scale": 1.2
  }
}
```

## Determinism Guarantees

- Base theme normalization is stable (`high-contrast` -> `high_contrast`).
- Token ordering follows the fixed token order.
- Manifest `theme.tokens`, `theme.config.overrides`, and `theme.definition` maps are sorted deterministically.
- Rebuilding a manifest from identical source and state yields identical `theme` payloads.

## CLI Scaffolding

Use `n3 create theme`:

```bash
n3 create theme enterprise_brand dark
```

This writes `themes/enterprise-brand.json` with deterministic key ordering.

## Accessibility Defaults

Theme variables drive focus and contrast-sensitive surfaces:

- `--n3-focus-ring`
- `--n3-border-color`
- `--n3-error-color`
- `--n3-error-surface`

Layout and interaction styles now consume these variables in:

- `src/namel3ss/studio/web/styles/layout_tokens.css`
- `src/namel3ss/studio/web/styles/chat.css`
- `src/namel3ss/studio/web/styles/drawer.css`
- `src/namel3ss/studio/web/styles/empty_states.css`
