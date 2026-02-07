# Extensions and Trust

Namel3ss community extensions are package folders with a manifest (`plugin.yaml` or `plugin.json`).
The manifest declares metadata, permissions, hooks, and API compatibility in a deterministic format.

## Capabilities

Add these capability tokens in `app.ai`:

```ai
capabilities:
  extension_hooks
  extension_trust
```

- `extension_hooks`: required when a plug-in manifest declares `hooks`.
- `extension_trust`: required for install, update, trust, revoke workflows and for loading permissioned plug-ins.

## Manifest schema

Minimal extension manifest:

```yaml
name: timeline-panel
version: "0.1.0"
author: ACME Labs
description: Studio timeline diagnostics panel
permissions:
  - ui
  - memory:read
hooks:
  studio: timeline/hooks.py
min_api_version: 1
signature: "optional-signature"
module: renderer.py
components:
  - name: TimelinePanel
    props:
      events: state_path
```

Supported permissions:

- `net`
- `file:read`
- `file:write`
- `db`
- `ui`
- `tool`
- `memory`
- `memory:read`
- `memory:write`
- `legacy_full_access` (compatibility fallback for old manifests with no `permissions` field)

Supported hook types:

- `compiler`
- `runtime`
- `studio`

## Trust model

Trusted entries are stored in:

- `.namel3ss/trusted_extensions.yaml`

Each trusted record includes:

- `name`
- `version`
- `hash` (deterministic package tree hash)
- `trusted_at`
- `permissions`
- `author`

## CLI workflows

Discover and inspect:

```bash
n3 plugin search timeline --json
n3 plugin info timeline-panel@0.1.0 --json
```

Install with explicit consent:

```bash
n3 plugin install timeline-panel@0.1.0 --yes --json
```

Manage trust:

```bash
n3 plugin trust timeline-panel@0.1.0 --yes --json
n3 plugin revoke timeline-panel@0.1.0 --json
```

List installed extensions:

```bash
n3 plugin list --installed --json
```

Update:

```bash
n3 plugin update timeline-panel --yes --json
```

## Determinism and safety

- Extension permissions are explicit and validated at parse/install time.
- Unknown permissions or invalid manifest fields fail deterministically.
- Registry and installed listings are returned in stable sorted order.
- Permissioned and hook-enabled plug-ins require trust and capability gates.
- Package trust is tied to immutable content hash.
