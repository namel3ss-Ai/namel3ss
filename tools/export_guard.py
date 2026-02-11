from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.export.guard import filter_export_actions


def guard_manifest_for_export(manifest: dict) -> dict:
    payload = dict(manifest) if isinstance(manifest, dict) else {}
    actions = payload.get("actions")
    action_map = actions if isinstance(actions, dict) else {}
    filtered, skipped = filter_export_actions(action_map)
    payload["actions"] = filtered
    payload["export_guard"] = {"skipped": skipped}
    return payload


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter unsupported action exports deterministically.")
    parser.add_argument("manifest", nargs="?", help="Path to manifest JSON. Reads stdin when omitted.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when unsupported actions were removed.",
    )
    return parser.parse_args(argv)


def _load_payload(path: str | None) -> dict:
    if path:
        raw = Path(path).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()
    loaded = json.loads(raw) if raw.strip() else {}
    return loaded if isinstance(loaded, dict) else {}


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    payload = _load_payload(args.manifest)
    guarded = guard_manifest_for_export(payload)
    skipped = guarded.get("export_guard", {}).get("skipped", [])
    print(canonical_json_dumps(guarded, pretty=True))
    if args.check and isinstance(skipped, list) and skipped:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
