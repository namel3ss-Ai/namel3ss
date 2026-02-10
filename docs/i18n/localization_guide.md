# Localization Guide

## Overview

Phase 5 localization adds deterministic i18n support via runtime configuration and translation bundles.

## Capability

- `ui.i18n` enables runtime locale selection and i18n manifest metadata.
- Without `ui.i18n`, runtime keeps default locale behavior and emits deterministic warnings in `manifest.i18n.warnings`.

## Configuration Contract

Provide `program.i18n_config` (or equivalent runtime injection) with:

```json
{
  "locale": "en",
  "fallback_locale": "en",
  "locales": ["en", "fr", "ar"],
  "translations": {
    "en": "i18n/locales/en.json",
    "fr": "i18n/locales/fr.json",
    "ar": "i18n/locales/ar.json"
  }
}
```

## Translation Bundles

Bundle format:

```json
{
  "locale": "fr",
  "fallback_locale": "en",
  "messages": {
    "manifest.pages.0.title": {
      "fr": "Assistant",
      "en": "Assistant"
    }
  }
}
```

## Extracting Strings

Use `namel3ss.i18n.i18n_extractor.extract_manifest_strings(manifest)` to build deterministic message keys.

Then write a seed catalog with `write_translation_catalog(...)`.

## Runtime Application

Use `namel3ss.i18n.translation_loader.localize_manifest` to apply translations and RTL direction.

- Missing keys are recorded in `manifest.i18n.missing_keys`.
- Fallback locale is applied deterministically.

## Locale Formatting

Use `namel3ss.i18n.locale_formatter` for deterministic locale rendering:

- `format_number`
- `format_date`
- `format_time`
- `format_datetime`

## RTL Behavior

`namel3ss.i18n.rtl_utils` determines direction by locale and mirrors layout slots for RTL contexts.

Studio/runtime renderer now sets:

- `document.documentElement.dir`
- `document.documentElement.lang`
- `body[data-direction]`
