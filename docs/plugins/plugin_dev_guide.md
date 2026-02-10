# Plugin Developer Guide

## Overview

Phase 5 plugin architecture adds deterministic plugin contracts with sandboxed rendering and explicit capabilities.

## Capability

- `ui.plugins` is the primary plugin capability.
- Legacy compatibility (`custom_ui` + `sandbox`) is still supported.
- Without plugin capability, plugin declarations are rejected outside Studio.

## Plugin Manifest Contract

`src/namel3ss/plugins/plugin_manifest.py` defines canonical contracts:

- `name`
- `version`
- `capabilities`
- `permissions`
- `components`
- `entry_point`

Validation is deterministic and sorted by component/property names.

## Loading and Registry

Use:

- `build_plugin_registry_contract(...)` for deterministic registry manifests
- `load_plugins(...)` for capability-gated sandbox loading

Loading order is stable (`name`, `version`).

## Sandbox Model

Runtime execution delegates to existing sandboxed UI plugin loader (`namel3ss.ui.plugins`).

This forbids arbitrary function calls and attribute access in plugin render expressions.

## Whitelisted Runtime API

`src/namel3ss/plugins/plugin_api.py` exposes:

- `read_state(path)`
- `has_action(action_id)`
- `theme_token(token_name)`
- `translate(key, default)`

No filesystem or network operations are exposed by this API surface.

## Scaffolding

`n3 create plugin <name>` now scaffolds:

- `plugin.json`
- `renderer.py`
- `assets/runtime.js`
- `assets/style.css`
- `translations/en.json`

## Studio Integration

New Studio components:

- `PluginManager.vue`
- `LocaleSelector.vue`

These provide deterministic plugin toggle and locale preview controls.
