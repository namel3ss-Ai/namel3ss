# App Permissions

Namel3ss supports an explicit application permission model for UI/runtime governance.

## Capability gate

`permissions:` requires the `app_permissions` capability.

```ai
spec is "1.0"

capabilities:
  app_permissions

permissions:
  ai:
    call: allowed
    tools: denied
```

If `permissions:` is declared without `app_permissions`, compilation fails.

## Domains and actions

Supported permissions are:

- `ai.call`
- `ai.tools`
- `uploads.read`
- `uploads.write`
- `ui_state.persistent_write`
- `navigation.change_page`

Syntax:

```ai
permissions:
  <domain>:
    <action>: allowed | denied
```

Rules:

- Missing permission entries default to `denied` when `permissions:` is declared.
- Permission checks are deterministic.
- Permission violations fail at compile time when statically detectable.
- Dynamic violations fail at runtime with deterministic error messages.

## Backward compatibility mode

Apps that do not declare `permissions:` run in legacy permissive mode.

- Existing behavior is preserved.
- The compiler records a governance warning recommending explicit permissions.

For production, declare `permissions:` explicitly and keep only the minimum required actions as `allowed`.
