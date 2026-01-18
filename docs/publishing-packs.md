# Publishing Packs (Local-First)

Packs are published locally and indexed in the local registry. There is no public registry yet.

## Quick path
```bash
n3 packs init team.pack
n3 packs validate ./team.pack --strict
n3 packs review ./team.pack --json
n3 packs sign ./team.pack --key-id "maintainer.alice" --private-key ./alice.key
n3 packs bundle ./team.pack --out ./dist
n3 registry add ./dist/team.pack.n3pack.zip
n3 registry build
```

## Install and enable
```bash
n3 pack add ./dist/team.pack.n3pack.zip
n3 packs keys add --id "maintainer.alice" --public-key ./alice.pub
n3 packs verify team.pack
n3 packs enable team.pack
```

## Notes
- Bundles are deterministic and exclude transient files.
- `n3 packs review --json` emits a machine-readable intent summary (save as `intent.json` if desired).
- `intent.md` is required and must include the frozen headings.
- Non-pure tools must declare capabilities in `capabilities.yaml`.
- `signature.txt` is digest-based and verifiable offline.
