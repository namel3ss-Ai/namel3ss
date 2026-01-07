# Tool packs

Tool packs are reusable tool bundles. namel3ss ships built-in packs and can install
local packs from disk. Packs can also be published to a local registry for intent-based
discovery. Pack tools are still English-first: you declare and call them by name,
without module:function wiring in `.ai`.

## Built-in packs
Built-in packs require no extra dependencies and are pre-bound.
Note: list aggregations (`sum/min/max/mean/median`) are built-in expressions; the math pack remains available for tool-call workflows.

### text
Available tools:
- "convert text to lowercase"
- "convert text to uppercase"
- "slugify text"
- "trim text"

Payloads:
- lowercase/uppercase/trim: `{ "text": "..." }`
- slugify: `{ "text": "...", "separator"?: "-" }`

### datetime
Available tools:
- "get current date and time"
- "parse date and time"
- "format date and time"

Payloads:
- now: `{ "timezone"?: "utc" | "local" }`
- parse: `{ "text": "...", "format"?: "%Y-%m-%d" }`
- format: `{ "iso": "...", "format": "%Y-%m-%d" }`

### file
Available tools:
- "read text file"
- "write text file"
- "read json file"
- "write json file"

Payloads:
- read_text: `{ "path": "data/file.txt", "encoding"?: "utf-8" }`
- write_text: `{ "path": "data/file.txt", "text": "...", "encoding"?: "utf-8", "create_dirs"?: true }`
- read_json: `{ "path": "data/file.json", "encoding"?: "utf-8" }`
- write_json: `{ "path": "data/file.json", "data": {...}, "encoding"?: "utf-8", "create_dirs"?: true }`

## Local packs (installed)
Local packs live under `.namel3ss/packs/<pack_id>` and ship their own bindings.
They must be verified and enabled before use.

## Authoring (local-first)
Create a pack folder with intent and capability scaffolding:
```bash
n3 packs init team.pack
n3 packs init team.nocode --no-code
```

`intent.md` is required and must include the frozen headings:
- What this pack does
- Tools provided (English)
- Inputs/outputs summary
- Capabilities & risk
- Failure modes
- Runner requirements

Validate and review before publishing:
```bash
n3 packs validate ./team.pack --strict
n3 packs review ./team.pack --json
```

## Publishing (review → bundle → sign)
Publishing is local and explicit:
```bash
n3 packs bundle ./team.pack --out ./dist
n3 packs sign ./team.pack --key-id "maintainer.alice" --private-key ./alice.key
```

Distribute the `.n3pack.zip` and install locally:
```bash
n3 packs add ./dist/team.pack-0.1.0.n3pack.zip
```

Add the bundle to the local registry for discovery:
```bash
n3 registry add ./dist/team.pack-0.1.0.n3pack.zip
n3 registry build
```

Install, verify, enable:
```bash
n3 packs add ./my_pack
n3 packs keys add --id "maintainer.alice" --public-key ./alice.pub
n3 packs keys list
n3 packs verify my.pack
n3 packs enable my.pack
```

Install by id from the registry:
```bash
n3 packs add team.pack@0.1.0
```

Check status or remove:
```bash
n3 packs status
n3 packs disable my.pack
n3 packs remove my.pack --yes
```

## Pack manifest (v1)
Each pack includes `pack.yaml` with metadata:
```yaml
id: "pack.slug"
name: "Sample Pack"
version: "0.1.0"
description: "Example tools"
author: "Team"
license: "MIT"
tools:
  - "greet someone"
```

Pack manifests are frozen at `pack_manifest` v1 (see `resources/spec_versions.json`).

Bindings come from `tools.yaml` (preferred) or `entrypoints` in `pack.yaml`.
`tools.yaml` uses the same schema as app bindings.

## Capabilities (v1)
Packs declare capabilities in `capabilities.yaml`:
```yaml
capabilities:
  "tool name":
    filesystem: "read"   # none | read | write
    network: "outbound"  # none | outbound
    env: "read"          # none | read
    subprocess: "none"   # none | allow
    secrets: ["API_KEY"] # optional
```

Rules:
- Non-pure tools must declare capabilities.
- `runner: service` requires `network: "outbound"`.
- `runner: container` requires `subprocess: "allow"`.

## Guarantees and enforcement
Runtime enforces capability guarantees on every tool call. Packs provide the
baseline via `capabilities.yaml`, and apps can further downgrade using
`[capability_overrides]` in `namel3ss.toml`. Trust policy can also restrict
capabilities. See `docs/capabilities.md` for the full model.

Coverage notes (v1):
- Local pack tools run with sandbox enforcement by default.
- Service runners should support the capability handshake.
- Container runners must declare enforcement (`declared` or `verified`).

## Trust model (v1)
Verification is a digest-based signature:
- `signature.txt` contains the digest of `pack.yaml` + `tools.yaml`.
- Trusted keys live in `.namel3ss/trust/keys.yaml`.
- Verification writes `verification.json` inside the pack directory.

Pack trust is frozen at v1 alongside the pack manifest (see `resources/spec_versions.json`).
Signer metadata is recorded in `pack.yaml` (`signer_id`, `signed_at`, `digest`).

Unverified packs are inactive and cannot run by default.

## Registry discovery (v1)
Discover packs by intent, capability, and trust:
```bash
n3 discover "send email securely"
n3 discover "webhook" --capability network --risk medium
```

## Example
```ai
tool "convert text to lowercase":
  implemented using python

  input:
    text is text

  output:
    text is text

flow "demo":
  let result is convert text to lowercase:
    text is "Hello World"
  return result
```

No bindings are required for built-in packs.
Pack tools bypass `.namel3ss/tools.yaml` and ignore runner settings.

## Precedence and collisions
Resolution order:
1) Built-in packs
2) Installed packs (verified + enabled)
3) App bindings (`.namel3ss/tools.yaml`)

If a binding uses the same English name as a pack tool, namel3ss treats it as a collision
and fails lint/doctor/runtime. Rename the tool or remove the binding.

If multiple packs provide the same tool, namel3ss reports a collision. Disable one pack
or pin the tool to a specific pack in `namel3ss.toml`:
```toml
[tool_packs]
enabled_packs = ["pack.a", "pack.b"]
pinned_tools = { "collision tool" = "pack.a" }
```
