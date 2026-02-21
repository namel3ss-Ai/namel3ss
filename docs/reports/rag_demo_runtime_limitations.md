# RAG Demo Runtime Limitations Report

Date: 2026-02-13  
Scope: `apps/rag-demo`  
Runtime target: `namel3ss==0.1.0a23`

## Constraint

Implementation changes are Namel3ss-first.  
If a limitation cannot be implemented in Namel3ss DSL, it is documented here for platform/runtime action.

## Limitation Feasibility Matrix

1. Static-vs-runtime manifest drift
- Namel3ss DSL feasibility: **No (platform responsibility)**
- Status: **Resolved in runtime startup gate**
- Platform implementation:
  - `src/namel3ss/runtime/server/startup/startup_context.py`
    - `require_static_runtime_manifest_parity`
    - `build_static_startup_manifest_payload`
    - `RUNTIME_MANIFEST_DRIFT_ERROR_CODE`
  - Enforced at startup in:
    - `src/namel3ss/runtime/server/dev/app.py`
    - `src/namel3ss/runtime/server/prod/app.py`
    - `src/namel3ss/runtime/server/service_manager.py`
- Verification:
  - `tests/runtime/test_runtime_manifest_parity_gate.py`
  - `tests/runtime/test_runtime_startup_locking.py`

2. Missing renderer-registry diagnostics endpoint
- Namel3ss DSL feasibility: **No (platform responsibility)**
- Status: **Resolved**
- Platform implementation:
  - `src/namel3ss/runtime/router/renderer_registry_health.py`
  - `src/namel3ss/runtime/ui/renderer/registry_health_contract.py`
  - Route: `GET /api/renderer-registry/health`
- Verification:
  - `tests/runtime/test_renderer_registry_health_route.py`

3. Multiple runtime processes bound to same host/port
- Namel3ss DSL feasibility: **No (platform responsibility)**
- Status: **Resolved**
- Platform implementation:
  - `src/namel3ss/runtime/server/lock/port_lock.py`
  - Lock key per `(host, port)` with explicit conflict error messaging.
- Verification:
  - `tests/runtime/test_runtime_startup_locking.py`

4. Multi-app path mis-targeting
- Namel3ss DSL feasibility: **Partial**
- Status: **Resolved for CLI targeting visibility**
- Platform implementation:
  - `src/namel3ss/cli/app_path.py`
  - `src/namel3ss/cli/workspace/app_path_resolution.py`
  - `src/namel3ss/cli/workspace/resolution_warning.py`
  - Emits selected app path and alternatives when multiple app roots exist.
- Verification:
  - `tests/cli/test_workspace_app_resolution.py`

5. Missing startup banner (`effective app path + manifest hash`)
- Namel3ss DSL feasibility: **No (platform responsibility)**
- Status: **Resolved**
- Platform implementation:
  - `src/namel3ss/runtime/server/startup/startup_context.py`
  - `src/namel3ss/runtime/server/startup/startup_banner.py`
  - Banner includes app path, bind host/port, manifest hash, renderer registry status/hash, lock path/pid.
- Verification:
  - `tests/runtime/test_runtime_startup_banner.py`
  - `tests/runtime/test_runtime_startup_locking.py`
