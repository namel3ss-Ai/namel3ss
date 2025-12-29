# Phase B1: exists

`n3 exists` compiles a namel3ss source file into a deterministic contract summary.

## What it is
- A stable summary of what the program defines and requires.
- A deterministic artifact pack written to disk.

## What it includes
- Spec version and source hash.
- Program summary (counts + names).
- Features used.
- Capabilities required.
- Deterministic warnings when applicable.

## What it does NOT include
- Flow execution or runtime side effects.
- Config loading or environment checks.
- Network or filesystem claims unless declared in the IR.

## Artifacts
Artifacts are written under:
- `.namel3ss/contract/last.json`
- `.namel3ss/contract/last.plain`
- `.namel3ss/contract/last.exists.txt`
- `.namel3ss/contract/history/<source_hash>.json`
