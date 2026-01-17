__all__ = ["Executor", "ExecutionResult", "execute_flow", "execute_program_flow"]


def __getattr__(name: str):
    if name in {"Executor", "ExecutionResult", "execute_flow", "execute_program_flow"}:
        from namel3ss.runtime.executor.api import Executor, ExecutionResult, execute_flow, execute_program_flow

        return {
            "Executor": Executor,
            "ExecutionResult": ExecutionResult,
            "execute_flow": execute_flow,
            "execute_program_flow": execute_program_flow,
        }[name]
    raise AttributeError(f"module 'namel3ss.runtime.executor' has no attribute {name!r}")
