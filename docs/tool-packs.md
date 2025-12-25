# Tool packs

Tool packs are reusable tool bundles. namel3ss ships built-in packs and can install
local packs from disk. Pack tools are still English-first: you declare and call them
by name, without module:function wiring in `.ai`.

## Built-in packs
Built-in packs require no extra dependencies and are pre-bound.

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

Install, verify, enable:
```bash
n3 packs add ./my_pack
n3 packs keys add --id "maintainer.alice" --public-key ./alice.pub
n3 packs verify my.pack
n3 packs enable my.pack
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

Bindings come from `tools.yaml` (preferred) or `entrypoints` in `pack.yaml`.
`tools.yaml` uses the same schema as app bindings.

## Trust model (v1)
Verification is a digest-based signature:
- `signature.txt` contains the digest of `pack.yaml` + `tools.yaml`.
- Trusted keys live in `.namel3ss/trust/keys.yaml`.
- Verification writes `verification.json` inside the pack directory.

Unverified packs are inactive and cannot run by default.

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
