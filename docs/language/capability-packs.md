# Capability Packs

Capability Packs are governed bundles of tools and permissions. They let apps use extended capabilities without managing dependencies.

## Structure
- `pack.yaml`: manifest (id, name, version, description, author, license, tools).
- `tools.yaml`: bindings for each tool in the pack.
- `capabilities.yaml`: per-tool permissions (filesystem, network, env, subprocess, secrets).
- `intent.md`: short human description of what the pack provides.
- `tools/` and optional `src/`: executable logic for the pack tools.

## Declaring packs in apps
Packs are explicit in the language:

```
packs:
  "builtin.text"
  "example.greeting"
```

Tools provided by packs are resolved only when the pack id is listed in the packs block.
Declare each pack tool in your app to define its input/output fields; the pack supplies bindings and permissions.

## Local packs
Local packs live under `packs/capability/<pack_id>/` in the project root. They are loaded deterministically and are inspected the same way as installed packs.

## Permissions and governance
- Pack permissions are deny-by-default; missing permissions default to no access.
- Trust policy at `.namel3ss/trust/policy.toml` can restrict or block pack usage.
- Policy decisions are enforced at runtime and surfaced in Studio explain output.

## Execution and inspection
- Tool calls record pack metadata (pack id, name, version).
- Capability checks include pack permission grants and denials.
- Studio and CLI use the same manifests and capability summaries.

## CLI
- `n3 pack list`
- `n3 pack info <pack_id>`

## Related docs
- `docs/tool-packs.md` for detailed pack tooling.
- `docs/capabilities.md` for capability enforcement details.
- `docs/trust-and-governance.md` for trust and signature coverage.
