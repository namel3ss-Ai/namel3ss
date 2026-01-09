from __future__ import annotations

import json
from pathlib import Path

from namel3ss.beta_lock.surfaces import SURFACES_PATH, load_surfaces
from namel3ss.evals.model import EVAL_SCHEMA_VERSION
from namel3ss.traces.schema import TRACE_VERSION


def test_beta_surfaces_catalog_is_valid():
    surfaces = load_surfaces()
    assert surfaces
    ids = [surface.surface_id for surface in surfaces]
    assert len(ids) == len(set(ids))

    lookup = {surface.surface_id: surface for surface in surfaces}
    assert lookup["trace_schema"].version == TRACE_VERSION
    assert lookup["cli.eval"].version == EVAL_SCHEMA_VERSION

    root = Path(__file__).resolve().parents[2]
    for surface in surfaces:
        for artifact in surface.artifacts:
            path = root / artifact
            assert path.exists(), f"missing artifact: {artifact}"
            if path.suffix == ".json":
                json.loads(path.read_text(encoding="utf-8"))


def test_beta_surfaces_schema_version_is_present():
    payload = json.loads(SURFACES_PATH.read_text(encoding="utf-8"))
    assert payload.get("schema_version") == "beta_surfaces.v1"
