import os
import sys
import shutil
import tempfile
import stat
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
if not sys.pycache_prefix:
    sys.pycache_prefix = str(Path(tempfile.gettempdir()) / "namel3ss_pycache")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from namel3ss.ir.nodes import lower_program  # noqa: E402
from namel3ss.parser.core import parse  # noqa: E402
from namel3ss.runtime.executor import Executor  # noqa: E402
from namel3ss.pipelines.registry import pipeline_contracts  # noqa: E402


def _ensure_spec(code: str) -> str:
    for line in code.splitlines():
        if line.strip().startswith('spec is "'):
            return code
    return 'spec is "1.0"\n\n' + code.lstrip("\n")


def parse_program(code: str):
    """Parse source into an AST program."""
    return parse(_ensure_spec(code))


def lower_ir_program(code: str):
    """Parse then lower to IR Program."""
    return lower_program(parse_program(code))


def run_flow(
    code: str,
    flow_name: str = "demo",
    initial_state=None,
    store=None,
    identity=None,
    input_data=None,
    project_root=None,
    app_path=None,
):
    """Parse, lower, and execute a flow by name."""
    ir_program = lower_ir_program(code)
    if project_root is not None:
        ir_program.project_root = str(project_root)
    if app_path is not None:
        ir_program.app_path = str(app_path)
    flow = next((f for f in ir_program.flows if f.name == flow_name), None)
    if flow is None:
        raise ValueError(f"Flow '{flow_name}' not found")
    schemas = {schema.name: schema for schema in ir_program.records}
    executor = Executor(
        flow,
        schemas=schemas,
        initial_state=initial_state,
        store=store,
        input_data=input_data,
        functions=ir_program.functions,
        flows={flow.name: flow for flow in ir_program.flows},
        flow_contracts=getattr(ir_program, "flow_contracts", {}) or {},
        pipeline_contracts=pipeline_contracts(),
        runtime_theme=getattr(ir_program, "theme", None),
        capabilities=getattr(ir_program, "capabilities", ()),
        identity_schema=getattr(ir_program, "identity", None),
        identity=identity,
        pack_allowlist=getattr(ir_program, "pack_allowlist", None),
        policy=getattr(ir_program, "policy", None),
        project_root=project_root,
        app_path=app_path,
    )
    return executor.run()


@pytest.fixture(autouse=True)
def _secret_audit_path(tmp_path, monkeypatch):
    monkeypatch.setenv("N3_SECRET_AUDIT_PATH", str(tmp_path / "secret_audit.jsonl"))


__all__ = ["parse_program", "lower_ir_program", "run_flow"]


_BASELINE_DIRTY: set[str] | None = None


def pytest_sessionstart(session):
    global _BASELINE_DIRTY
    from namel3ss.beta_lock.repo_clean import repo_dirty_entries

    root = Path(__file__).resolve().parents[1]
    _remove_runtime_artifacts(root)
    _BASELINE_DIRTY = set(repo_dirty_entries(root))


def pytest_sessionfinish(session, exitstatus):
    from namel3ss.beta_lock.repo_clean import repo_dirty_entries

    root = Path(__file__).resolve().parents[1]
    bytecode = _find_bytecode_artifacts(root)
    if bytecode:
        joined = "\n".join(bytecode)
        raise AssertionError(f"Bytecode artifacts found:\n{joined}")
    baseline = _BASELINE_DIRTY or set()
    current = set(repo_dirty_entries(root))
    new_dirty = sorted(current - baseline)
    if new_dirty:
        joined = "\n".join(new_dirty)
        raise AssertionError(f"Repository dirty after tests:\\n{joined}")


def _remove_runtime_artifacts(root: Path) -> None:
    pytest_cache = root / ".pytest_cache"
    if pytest_cache.exists():
        _force_remove_dir(pytest_cache)
    build_cache = root / ".namel3ss"
    if build_cache.exists():
        _force_remove_dir(build_cache)
    for cache in root.rglob("__pycache__"):
        if cache.exists():
            _force_remove_dir(cache)
    for pyc in root.rglob("*.pyc"):
        try:
            pyc.unlink()
        except FileNotFoundError:
            pass


def _find_bytecode_artifacts(root: Path) -> list[str]:
    artifacts: list[str] = []
    for cache in root.rglob("__pycache__"):
        if ".git" in cache.parts:
            continue
        artifacts.append(str(cache.relative_to(root)))
    for pyc in root.rglob("*.pyc"):
        if ".git" in pyc.parts:
            continue
        artifacts.append(str(pyc.relative_to(root)))
    return sorted(set(artifacts))


def _force_remove_dir(path: Path) -> None:
    def _onerror(func, target, exc_info):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except Exception:
            pass

    shutil.rmtree(path, ignore_errors=False, onerror=_onerror)


def pytest_configure(config):
    config.addinivalue_line("markers", "network: requires network access")
    config.addinivalue_line("markers", "slow: slow integration tests")
