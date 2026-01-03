from namel3ss.runtime.build.explain.collect import collect_inputs
from namel3ss.runtime.build.explain.diff import diff_manifests
from namel3ss.runtime.build.explain.fingerprint import compute_build_id
from namel3ss.runtime.build.explain.guarantees import infer_guarantees
from namel3ss.runtime.build.explain.manifest import BuildManifest
from namel3ss.runtime.build.explain.store import write_history


def test_build_explain_imports() -> None:
    assert callable(collect_inputs)
    assert callable(diff_manifests)
    assert callable(compute_build_id)
    assert callable(infer_guarantees)
    assert callable(write_history)
    assert isinstance(BuildManifest, type)
