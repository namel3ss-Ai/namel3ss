# Registry (Intent Graph)

The namel3ss registry is not a package store. It is an intent graph:
metadata about packs and tools, indexed by intent phrases, capabilities, and trust.
Registry entries never execute code.

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
n3 discover "send email securely"
n3 discover "invoice pdf" --capability filesystem
n3 discover "webhook" --risk medium
```

Capability filters use declared pack capabilities; policy downgrades can still
block installation or enabling. Results include a "blocked by policy" label
when applicable.

Install by id once you decide:
```bash
n3 pack add team.pack
n3 pack add team.pack --registry team
n3 pack add team.pack --offline
```

Ranking:
1) trusted signature (verified + trusted key)
2) lower risk
3) intent token overlap

Matches include a short "why this matched" summary and policy gates.

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
