# Capability Packs

Capability Packs are governed bundles of tools and permissions. They let apps use extended capabilities without managing dependencies.

## Structure
- `pack.yaml`: manifest (id, name, version, description, author, license, tools).
- `tools.yaml` or entrypoints in `pack.yaml`: bindings for each tool in the pack.
- `capabilities.yaml`: per-tool permissions (filesystem, network, env, subprocess, secrets).
- `intent.md`: short human description of what the pack provides.
- `signature.txt`: cryptographic signature for verification.
- `tools/` and optional `src/`: executable logic for the pack tools.
- `tests/`: deterministic test cases for pack tools.

## Declaring packs in apps
Packs are explicit in the language:

```
packs:
  "builtin.text"
  "example.greeting"
```

Tools provided by packs are resolved only when the pack id is listed in the packs block.
Declare each pack tool in your app to define its input/output fields; the pack supplies bindings and permissions.
Built-in packs follow the same rule: list `builtin.*` packs explicitly.

## Local packs
Local packs live under `packs/capability/<pack_id>/` in the project root. They are loaded deterministically and are inspected the same way as installed packs.
Local packs still require signing unless trust policy explicitly allows unsigned use.

## Signing and trust
- Packs are signed with `n3 pack sign` and embed signer metadata in `pack.yaml`.
- Trusted signers live in `.namel3ss/trust/keys.yaml`.
- Unsigned packs are rejected by default unless trust policy allows them.
- Verification is deterministic and recorded in pack inspection output.

## Permissions and governance
- Pack permissions are deny-by-default; missing permissions default to no access.
- Trust policy at `.namel3ss/trust/policy.toml` can restrict or block pack usage.
- Policy decisions are enforced at runtime and surfaced in Studio explain output.

## Registry and install
- Packs can be installed by name from a registry index.
- Registry entries include intent text, capabilities, risk, signatures, and trust status.
- `n3 pack add <pack_name>` installs from the default registry.
- `n3 pack add <pack_name>@<version>` installs a specific version.
- `n3 pack add <pack_name> --registry <alias-or-url>` targets a specific registry.
- `n3 pack add <pack_name> --offline` uses local cache only.
- Local bundle installs remain supported by path.
- `n3 registry list | search | info` inspects available packs and versions.

## Sandboxing
- Pack tool execution is scoped to a runtime directory under `.namel3ss/`.
- Filesystem access is restricted to the pack runtime root unless explicitly allowed.
- Network access requires declared outbound permissions.
- Job and file effects are recorded deterministically in Studio explain output.

## Official packs
- Official packs live under `packs/official/` in the repo and are signed by maintainers.
- They provide stable contracts for common capabilities without dependencies.

## Authoring official packs
- Keep tool behavior deterministic and covered by `tests/cases.json`.
- Run `n3 packs sign` with a maintainer key, then verify with `n3 packs verify`.
- Submit changes to `packs/official/<pack_id>/` with manifest, bindings, capabilities, intent, and README.

## Execution and inspection
- Tool calls record pack metadata (pack id, name, version).
- Capability checks include pack permission grants and denials.
- Studio and CLI use the same manifests and capability summaries.

## CLI
- `n3 pack list`
- `n3 pack info <pack_id>`
- `n3 pack add <pack_name>`
- `n3 pack sign <pack_path>`
- `n3 pack verify <pack_id>`
- `n3 pack enable <pack_id>`
- `n3 pack status`

## Related docs
- `docs/tool-packs.md` for detailed pack tooling.
- `docs/capabilities.md` for capability enforcement details.
- `docs/trust-and-governance.md` for trust and signature coverage.
