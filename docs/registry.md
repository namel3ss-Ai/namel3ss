# Registry

The namel3ss registry is not a package store. It is a trusted index of intent, capability, and risk.
Registry entries store metadata about packs and tools, indexed by intent phrases, capabilities, and trust.
Registry entries never execute code.

Registry entries include:
- Pack name and version
- Intent text and intent phrases
- Capabilities and risk level
- Signature status and signer id
- Trust status (trusted, untrusted, blocked by policy)

## Local index (default)
Local registry entries live under:
- `.namel3ss/registry/index.jsonl` (append-only)
- `.namel3ss/registry/index_compact.json` (rebuilt by `n3 registry build`)

Add a bundle to the local registry:
```bash
n3 registry add ./dist/team.pack.n3pack.zip
n3 registry build
```

## Discover by intent
Search by intent phrase (English-first):
```bash
n3 registry search "send email securely"
n3 registry search "invoice pdf" --capability filesystem
n3 registry search "webhook" --risk medium
```

Capability filters use declared pack capabilities; policy downgrades can still
block installation or enabling. Results include a "blocked by policy" label
when applicable.

Inspect and list:
```bash
n3 registry list
n3 registry info team.pack
```

Install by id once you decide:
```bash
n3 pack add team.pack
n3 pack add team.pack@0.1.0
n3 pack add team.pack --registry team
n3 pack add team.pack --offline
```

Ranking:
1) trusted signature (verified + trusted key)
2) lower risk
3) intent token overlap

Matches include a short "why this matched" summary and policy gates.

## Versions
- Versions are simple semver (`major.minor.patch`) or `stable`.
- Compatibility is determined by major version; a major change is an incompatible upgrade.
- Upgrades are explicit; install a specific version to change what is installed.
- Registry info surfaces compatibility against the installed version.

## Trust and policy
Registry entries surface trust metadata:
- `signer_id` (optional)
- `verified_by` (trusted key ids)

By default, unverified installs are blocked. Use a trust policy to set limits:
```
.namel3ss/trust/policy.toml
```

Example:
```toml
allow_unverified_installs = false
allow_unverified_enable = false
max_risk = "medium"
allowed_capabilities = { network = "outbound", filesystem = "read", subprocess = "none" }
```

Policies also feed runtime guarantees; tools are downgraded at execution time
and denied if they exceed policy limits.

## Risk scoring
- low: no network, no fs write, no subprocess, no secrets
- medium: network outbound OR fs read OR env read OR secrets
- high: fs write OR subprocess OR container runner OR unknown capabilities

## Registry sources (federated)
Configure registries in `namel3ss.toml`:
```toml
[registries]
sources = [
  { id = "local", kind = "local_index", path = ".namel3ss/registry/index.jsonl" },
  { id = "team", kind = "http", url = "http://127.0.0.1:9898/registry" }
]
default = ["local"]
```

`local_index` is always supported. HTTP registries are optional and local-first.
Use `--offline` to avoid remote registry access.
