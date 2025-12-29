# Build Exists

Explainable builds show why this app exists in its current form.
Output is deterministic and based only on the app sources and build inputs.
It does not deploy or change runtime behavior.

## Quick use
Run the build explanation:
```bash
n3 exists
n3 exists --diff
```

## What it includes
- Build id and source fingerprint.
- Guarantees recorded by explain packs.
- Constraints inferred from capability overrides.
- Narrative diff vs the previous build.

## What it does not include
- Deployment steps.
- File-by-file diffs.
- Guarantees that are not recorded.

## Artifacts
The build explanation writes:
- `.namel3ss/build/last.json`
- `.namel3ss/build/last.plain`
- `.namel3ss/build/last.exists.txt`

History is stored at:
- `.namel3ss/build/history/<build_id>.json`
