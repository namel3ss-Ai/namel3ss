from __future__ import annotations

from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.runtime.contracts.runtime_schema import runtime_contract_schema_catalog


OUTPUT_PATH = Path("packages/namel3ss-client/src/runtime_contract_schema.json")


def main() -> int:
    payload = runtime_contract_schema_catalog()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(canonical_json_dumps(payload, pretty=True, drop_run_keys=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
