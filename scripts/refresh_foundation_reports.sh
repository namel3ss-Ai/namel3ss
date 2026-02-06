#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

python3 scripts/audit_codebase.py
python3 scripts/measure_baseline.py --timing deterministic

echo "Refreshed docs/reports/code_audit.md and docs/reports/baseline_metrics.json"
