# Error Conventions

> This document defines the canonical error and diagnostic conventions. It is authoritative and must remain stable.

## Scope
- Applies to parse, build, runtime, tool, provider, policy, and capability errors.
- Applies to diagnostics and warnings surfaced in validation.

## Error Types
- **Namel3ssError**: base error type with `message`, optional `line`/`column`, and optional `details`.
- Errors are formatted with a location prefix when line/column are present.

## Guidance Message Format
Guidance messages use a fixed four-line format:
- `What happened: ...`
- `Why: ...`
- `Fix: ...`
- `Example: ...`

## Canonical Error Catalog
The JSON below is the canonical, test-locked catalog of error categories and runtime templates.

<!-- CONTRACT:error_conventions -->
```json
{
  "categories": [
    "parse",
    "runtime",
    "tool",
    "provider",
    "capability",
    "policy",
    "internal"
  ],
  "default_codes": {
    "capability": "capability_denied",
    "internal": "internal_error",
    "parse": "parse_error",
    "policy": "policy_denied",
    "provider": "provider_error",
    "runtime": "runtime_error",
    "tool": "tool_error"
  },
  "fallback_messages": {
    "capability": "Capability error.",
    "internal": "Internal error.",
    "parse": "Parse error.",
    "policy": "Policy error.",
    "provider": "Provider error.",
    "runtime": "Runtime error.",
    "tool": "Tool error."
  },
  "kind_category_map": {
    "ai_provider": "provider",
    "capability": "capability",
    "diagnostics": "runtime",
    "engine": "internal",
    "internal": "internal",
    "manifest": "runtime",
    "parse": "parse",
    "policy": "policy",
    "provider": "provider",
    "runtime": "runtime",
    "tool": "tool",
    "tools": "tool"
  },
  "runtime_templates": {
    "runtime.ai.failed": {
      "example": null,
      "fix": [
        "Check the AI profile and inputs."
      ],
      "what": "AI call failed.",
      "why": [
        "The AI call did not complete."
      ]
    },
    "runtime.ai.provider_error": {
      "example": null,
      "fix": [
        "Check the AI provider configuration."
      ],
      "what": "AI provider error.",
      "why": [
        "The AI provider returned an error."
      ]
    },
    "runtime.engine.error": {
      "example": null,
      "fix": [
        "Review the error message and try again."
      ],
      "what": "Runtime error.",
      "why": [
        "The engine raised an error."
      ]
    },
    "runtime.fs.failed": {
      "example": null,
      "fix": [
        "Check file permissions and paths."
      ],
      "what": "Filesystem operation failed.",
      "why": [
        "The filesystem operation did not complete."
      ]
    },
    "runtime.memory.failed": {
      "example": null,
      "fix": [
        "Check memory configuration."
      ],
      "what": "Memory operation failed.",
      "why": [
        "The memory operation did not complete."
      ]
    },
    "runtime.memory.persist_failed": {
      "example": null,
      "fix": [
        "Check the project folder permissions."
      ],
      "what": "Memory persistence failed.",
      "why": [
        "Memory could not be saved."
      ]
    },
    "runtime.store.commit_failed": {
      "example": null,
      "fix": [
        "Check storage configuration and retry."
      ],
      "what": "Store commit failed.",
      "why": [
        "The storage commit did not complete."
      ]
    },
    "runtime.store.failed": {
      "example": null,
      "fix": [
        "Check storage configuration."
      ],
      "what": "Store operation failed.",
      "why": [
        "The storage operation did not complete."
      ]
    },
    "runtime.store.rollback_failed": {
      "example": null,
      "fix": [
        "Check storage health and retry."
      ],
      "what": "Store rollback failed.",
      "why": [
        "The storage rollback did not complete."
      ]
    },
    "runtime.theme.failed": {
      "example": null,
      "fix": [
        "Check the theme settings."
      ],
      "what": "Theme resolution failed.",
      "why": [
        "Theme could not be resolved."
      ]
    },
    "runtime.tools.blocked": {
      "example": null,
      "fix": [
        "Allow the required capability or remove the tool call."
      ],
      "what": "Tool call was blocked.",
      "why": [
        "Tool execution was blocked."
      ]
    },
    "runtime.tools.failed": {
      "example": null,
      "fix": [
        "Check tool bindings and inputs."
      ],
      "what": "Tool call failed.",
      "why": [
        "The tool call did not complete."
      ]
    }
  }
}
```
<!-- END_CONTRACT:error_conventions -->

## Error Entry Normalization
Error entries are normalized through `build_error_entry`:
- `category` is derived from error kind or traces.
- `code` is `details.error_id` (if present), else `kind`, else the default code for the category.
- `message` uses guidance `what` when present; otherwise a normalized message or fallback message.
- `location` includes `line`, `column`, and optional `file` (paths are normalized to project-relative).
- `hint` and `remediation` come from guidance `why` and `fix`.
- `trace_ref` uses `error_id`/`error_step_id` when present.
- `details` are normalized with stable key ordering and secret redaction.

## Runtime Error Pack
Runtime failures emit an `ErrorPack`:
- `error`: a `Namel3ssRuntimeError` with `error_id`, `kind`, `boundary`, `what`, `why`, `fix`, `example`, `where`, and `raw_message`.
- `summary`: includes `ok=false`, `flow_name`, `boundary`, and `kind`.
- `traces_tail`: redacted tail of traces (bounded length, stable ordering).

## Error Identifier Format
Runtime `error_id` values follow this deterministic pattern:
- `E-{BOUNDARY}-{KIND}-{FLOW}-{STATEMENT_KIND}-{INDEX}`
- Parts are uppercased, non-alphanumeric characters become `_`.
- Missing parts use fallbacks (`ENGINE`, `ERROR`, `NONE`); missing index defaults to `0`.
- `statement_index` is 1-based when available.

## Diagnostics and Warnings
- Validation warnings use `ValidationWarning` with `code`, `message`, `fix`, `path`, `line`, `column`, `category`, and `enforced_at`.
- Warning categories are derived from the code prefix (for example `state.*`, `identity.*`).
- Parse diagnostics may attach stable `error_id` values in `details` (for example `parse.reserved_identifier`).
