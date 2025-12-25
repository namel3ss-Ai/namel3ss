# Capabilities (v1)

Capabilities are enforced as negative guarantees. A guarantee says what a tool
*cannot* do, and the runtime proves it by blocking disallowed IO.

## Effective guarantees
Each tool invocation computes an effective guarantees object:
```
no_filesystem_write: true|false
no_filesystem_read: true|false
no_network: true|false
no_subprocess: true|false
no_env_read: true|false
no_env_write: true|false
secrets_allowed: ["NAME", ...]   # optional allowlist
```

Guarantees are derived from:
1) Pack capabilities (`capabilities.yaml`)
2) Tool purity (`purity is "pure"`)
3) User overrides (`namel3ss.toml`)
4) Trust policy (`.namel3ss/trust/policy.toml`)

Rules:
- Absence means "not guaranteed."
- Guarantees are monotonic: runtime may only tighten, never loosen.
- Policy and user overrides can only restrict further.

## Pack capabilities (source of truth)
Pack tools declare baseline capabilities in `capabilities.yaml`:
```yaml
capabilities:
  "send email securely":
    filesystem: "none"   # none | read | write
    network: "outbound"  # none | outbound
    env: "none"          # none | read
    subprocess: "none"   # none | allow
    secrets: ["SMTP_TOKEN"]
```

## User downgrades (per app)
Add capability overrides in `namel3ss.toml`:
```toml
[capability_overrides]
"send email securely" = { no_network = true }
"write text file" = { no_filesystem_write = true }
```

## Unsafe overrides (explicit)
You can bypass enforcement coverage checks for a tool:
```toml
[capability_overrides]
"send email securely" = { allow_unsafe_execution = true }
```

Unsafe overrides never loosen guarantees. They only allow execution when the
runner cannot prove enforcement. `n3 verify --prod` fails if any unsafe
overrides exist unless you pass `--allow-unsafe`.

## Policy downgrades (org or team)
Trust policy can enforce stricter caps in `.namel3ss/trust/policy.toml`:
```toml
allowed_capabilities = { network = "none", filesystem = "read" }
```

Policy never expands capabilities; it only restricts.

## Runtime enforcement
All side-effectful operations go through semantic IO gates:
- Filesystem read/write
- Network outbound HTTP
- Subprocess spawn
- Environment read/write

Denied operations emit a `capability_check` trace and fail with guidance.

## Coverage and sandbox (v1)
Enforcement coverage is runner-specific:
- `local`: enforced when sandbox is enabled.
- `service`: enforced only after a successful capability handshake.
- `container`: enforced only when enforcement is declared/verified.

Enable sandbox for user tools in `.namel3ss/tools.yaml`:
```yaml
tools:
  "my tool":
    kind: "python"
    entry: "tools.my_tool:run"
    sandbox: true
```

## Traces
Denied checks always emit:
```
{
  "type": "capability_check",
  "tool_name": "...",
  "runner": "local|service|container",
  "resolved_source": "builtin_pack|installed_pack|binding",
  "capability": "network|filesystem_write|...",
  "allowed": false,
  "guarantee_source": "tool|pack|user|policy",
  "reason": "guarantee_blocked",
  "protocol_version": 1
}
```

See `docs/trace-schema-v1.md` for the frozen schema.
