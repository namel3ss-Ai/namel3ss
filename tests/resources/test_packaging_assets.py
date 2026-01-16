from pathlib import Path


def test_packaging_includes_templates_examples_and_runtime() -> None:
    manifest = Path("MANIFEST.in").read_text(encoding="utf-8")
    for line in [
        "recursive-include src/namel3ss/templates *",
        "recursive-include src/namel3ss/examples *",
        "recursive-include src/namel3ss/runtime/web *",
    ]:
        assert line in manifest

    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    for block in [
        '"namel3ss.templates"',
        '"namel3ss.examples"',
        '"namel3ss.runtime"',
    ]:
        assert block in pyproject
