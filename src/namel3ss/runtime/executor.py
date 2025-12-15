from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.ai.provider import AIProvider, AIToolCallResponse
from namel3ss.runtime.ai.trace import AITrace
from namel3ss.runtime.records.service import save_record_or_raise
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.tools.registry import execute_tool
from namel3ss.schema.records import RecordSchema


@dataclass
class ExecutionResult:
    state: Dict[str, object]
    last_value: Optional[object]
    traces: list[AITrace]


class _ReturnSignal(Exception):
    """Internal control flow for return."""

    def __init__(self, value: object) -> None:
        super().__init__("return")
        self.value = value


class Executor:
    def __init__(
        self,
        flow: ir.Flow,
        schemas: Optional[Dict[str, RecordSchema]] = None,
        initial_state: Optional[Dict[str, object]] = None,
        store: Optional[MemoryStore] = None,
        input_data: Optional[Dict[str, object]] = None,
        ai_provider: Optional[AIProvider] = None,
        ai_profiles: Optional[Dict[str, ir.AIDecl]] = None,
        memory_manager: Optional[MemoryManager] = None,
        agents: Optional[Dict[str, ir.AgentDecl]] = None,
    ) -> None:
        self.flow = flow
        self.schemas = schemas or {}
        self.state: Dict[str, object] = initial_state or {}
        self.locals: Dict[str, object] = {"input": input_data or {}}
        self.constants: set[str] = set()
        self.last_value: Optional[object] = None
        self.store = store or MemoryStore()
        self.ai_provider = ai_provider or MockProvider()
        self.ai_profiles = ai_profiles or {}
        self.agents = agents or {}
        self.traces: list[AITrace] = []
        self.memory_manager = memory_manager or MemoryManager()
        self.agent_calls = 0

    def run(self) -> ExecutionResult:
        try:
            for stmt in self.flow.body:
                self._execute_statement(stmt)
        except _ReturnSignal as signal:
            self.last_value = signal.value
        return ExecutionResult(state=self.state, last_value=self.last_value, traces=self.traces)

    def _execute_statement(self, stmt: ir.Statement) -> None:
        if isinstance(stmt, ir.Let):
            value = self._evaluate_expression(stmt.expression)
            self.locals[stmt.name] = value
            if stmt.constant:
                self.constants.add(stmt.name)
            self.last_value = value
            return
        if isinstance(stmt, ir.Set):
            value = self._evaluate_expression(stmt.expression)
            self._assign(stmt.target, value, stmt)
            self.last_value = value
            return
        if isinstance(stmt, ir.If):
            condition_value = self._evaluate_expression(stmt.condition)
            if not isinstance(condition_value, bool):
                raise Namel3ssError(
                    "Condition must evaluate to a boolean",
                    line=stmt.line,
                    column=stmt.column,
                )
            branch = stmt.then_body if condition_value else stmt.else_body
            for child in branch:
                self._execute_statement(child)
            return
        if isinstance(stmt, ir.Return):
            value = self._evaluate_expression(stmt.expression)
            raise _ReturnSignal(value)
        if isinstance(stmt, ir.Repeat):
            count_value = self._evaluate_expression(stmt.count)
            if not isinstance(count_value, int):
                raise Namel3ssError("Repeat count must be an integer", line=stmt.line, column=stmt.column)
            if count_value < 0:
                raise Namel3ssError("Repeat count cannot be negative", line=stmt.line, column=stmt.column)
            for _ in range(count_value):
                for child in stmt.body:
                    self._execute_statement(child)
            return
        if isinstance(stmt, ir.ForEach):
            iterable_value = self._evaluate_expression(stmt.iterable)
            if not isinstance(iterable_value, list):
                raise Namel3ssError("For-each expects a list", line=stmt.line, column=stmt.column)
            for item in iterable_value:
                self.locals[stmt.name] = item
                for child in stmt.body:
                    self._execute_statement(child)
            return
        if isinstance(stmt, ir.Match):
            subject = self._evaluate_expression(stmt.expression)
            matched = False
            for case in stmt.cases:
                pattern_value = self._evaluate_expression(case.pattern)
                if subject == pattern_value:
                    matched = True
                    for child in case.body:
                        self._execute_statement(child)
                    break
            if not matched and stmt.otherwise is not None:
                for child in stmt.otherwise:
                    self._execute_statement(child)
            return
        if isinstance(stmt, ir.TryCatch):
            try:
                for child in stmt.try_body:
                    self._execute_statement(child)
            except Namel3ssError as err:
                self.locals[stmt.catch_var] = err
                for child in stmt.catch_body:
                    self._execute_statement(child)
            return
        if isinstance(stmt, ir.AskAIStmt):
            self._execute_ask_ai(stmt)
            return
        if isinstance(stmt, ir.RunAgentStmt):
            self._execute_run_agent(stmt)
            return
        if isinstance(stmt, ir.RunAgentsParallelStmt):
            self._execute_run_agents_parallel(stmt)
            return
        if isinstance(stmt, ir.Save):
            self._handle_save(stmt)
            return
        if isinstance(stmt, ir.Find):
            self._handle_find(stmt)
            return
        raise Namel3ssError(f"Unsupported statement type: {type(stmt)}", line=stmt.line, column=stmt.column)

    def _assign(self, target: ir.Assignable, value: object, origin: ir.Statement) -> None:
        if isinstance(target, ir.VarReference):
            if target.name not in self.locals:
                raise Namel3ssError(
                    f"Cannot set undeclared variable '{target.name}'",
                    line=origin.line,
                    column=origin.column,
                )
            if target.name in self.constants:
                raise Namel3ssError(
                    f"Cannot set constant '{target.name}'",
                    line=origin.line,
                    column=origin.column,
                )
            self.locals[target.name] = value
            return

        if isinstance(target, ir.StatePath):
            self._assign_state_path(target, value)
            return

        raise Namel3ssError(f"Unsupported assignment target: {type(target)}", line=origin.line, column=origin.column)

    def _assign_state_path(self, target: ir.StatePath, value: object) -> None:
        cursor: Dict[str, object] = self.state
        for segment in target.path[:-1]:
            if segment not in cursor or not isinstance(cursor[segment], dict):
                cursor[segment] = {}
            cursor = cursor[segment]  # type: ignore[assignment]
        cursor[target.path[-1]] = value

    def _evaluate_expression(self, expr: ir.Expression) -> object:
        if isinstance(expr, ir.Literal):
            return expr.value
        if isinstance(expr, ir.VarReference):
            if expr.name not in self.locals:
                raise Namel3ssError(
                    f"Unknown variable '{expr.name}'",
                    line=expr.line,
                    column=expr.column,
                )
            return self.locals[expr.name]
        if isinstance(expr, ir.AttrAccess):
            if expr.base not in self.locals:
                raise Namel3ssError(
                    f"Unknown variable '{expr.base}'",
                    line=expr.line,
                    column=expr.column,
                )
            value = self.locals[expr.base]
            for attr in expr.attrs:
                if isinstance(value, dict):
                    if attr not in value:
                        raise Namel3ssError(
                            f"Missing attribute '{attr}'",
                            line=expr.line,
                            column=expr.column,
                        )
                    value = value[attr]
                    continue
                if not hasattr(value, attr):
                    raise Namel3ssError(
                        f"Missing attribute '{attr}'",
                        line=expr.line,
                        column=expr.column,
                    )
                value = getattr(value, attr)
            return value
        if isinstance(expr, ir.StatePath):
            return self._resolve_state_path(expr)
        if isinstance(expr, ir.UnaryOp):
            operand = self._evaluate_expression(expr.operand)
            if expr.op == "not":
                if not isinstance(operand, bool):
                    raise Namel3ssError("Operand to 'not' must be boolean", line=expr.line, column=expr.column)
                return not operand
            raise Namel3ssError(f"Unsupported unary op '{expr.op}'", line=expr.line, column=expr.column)
        if isinstance(expr, ir.BinaryOp):
            if expr.op == "and":
                left = self._evaluate_expression(expr.left)
                if not isinstance(left, bool):
                    raise Namel3ssError("Left operand of 'and' must be boolean", line=expr.line, column=expr.column)
                if not left:
                    return False
                right = self._evaluate_expression(expr.right)
                if not isinstance(right, bool):
                    raise Namel3ssError("Right operand of 'and' must be boolean", line=expr.line, column=expr.column)
                return left and right
            if expr.op == "or":
                left = self._evaluate_expression(expr.left)
                if not isinstance(left, bool):
                    raise Namel3ssError("Left operand of 'or' must be boolean", line=expr.line, column=expr.column)
                if left:
                    return True
                right = self._evaluate_expression(expr.right)
                if not isinstance(right, bool):
                    raise Namel3ssError("Right operand of 'or' must be boolean", line=expr.line, column=expr.column)
                return bool(right)
            raise Namel3ssError(f"Unsupported binary op '{expr.op}'", line=expr.line, column=expr.column)
        if isinstance(expr, ir.Comparison):
            left = self._evaluate_expression(expr.left)
            right = self._evaluate_expression(expr.right)
            if expr.kind in {"gt", "lt"}:
                if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
                    raise Namel3ssError(
                        "Greater/less comparisons require numbers",
                        line=expr.line,
                        column=expr.column,
                    )
                return left > right if expr.kind == "gt" else left < right
            if expr.kind == "eq":
                return left == right
            raise Namel3ssError(f"Unsupported comparison '{expr.kind}'", line=expr.line, column=expr.column)

        raise Namel3ssError(f"Unsupported expression type: {type(expr)}", line=expr.line, column=expr.column)
    def _resolve_state_path(self, expr: ir.StatePath) -> object:
        cursor: object = self.state
        for segment in expr.path:
            if not isinstance(cursor, dict):
                raise Namel3ssError(
                    f"State path '{'.'.join(expr.path)}' is not a mapping",
                    line=expr.line,
                    column=expr.column,
                )
            if segment not in cursor:
                raise Namel3ssError(
                    f"Unknown state path '{'.'.join(expr.path)}'",
                    line=expr.line,
                    column=expr.column,
                )
            cursor = cursor[segment]
        return cursor
    def _handle_save(self, stmt: ir.Save) -> None:
        state_key = stmt.record_name.lower()
        data_obj = self.state.get(state_key)
        if not isinstance(data_obj, dict):
            raise Namel3ssError(
                f"Expected state.{state_key} to be a record dictionary",
                line=stmt.line,
                column=stmt.column,
            )
        validated = dict(data_obj)
        saved = save_record_or_raise(
            stmt.record_name,
            validated,
            self.schemas,
            self.state,
            self.store,
            line=stmt.line,
            column=stmt.column,
        )
        self.last_value = saved
    def _execute_ask_ai(self, expr: ir.AskAIStmt) -> str:
        if expr.ai_name not in self.ai_profiles:
            raise Namel3ssError(
                f"Unknown AI '{expr.ai_name}'",
                line=expr.line,
                column=expr.column,
            )
        profile = self.ai_profiles[expr.ai_name]
        user_input = self._evaluate_expression(expr.input_expr)
        if not isinstance(user_input, str):
            raise Namel3ssError("AI input must be a string", line=expr.line, column=expr.column)
        memory_context = self.memory_manager.recall_context(profile, user_input, self.state)
        tool_events: list[dict] = []
        response_output = self._run_ai_with_tools(profile, user_input, memory_context, tool_events)
        trace = AITrace(
            ai_name=expr.ai_name,
            ai_profile_name=expr.ai_name,
            agent_name=None,
            model=profile.model,
            system_prompt=profile.system_prompt,
            input=user_input,
            output=response_output,
            memory=memory_context,
            tool_calls=[e for e in tool_events if e.get("type") == "call"],
            tool_results=[e for e in tool_events if e.get("type") == "result"],
        )
        self.traces.append(trace)
        if expr.target in self.constants:
            raise Namel3ssError(f"Cannot assign to constant '{expr.target}'", line=expr.line, column=expr.column)
        self.locals[expr.target] = response_output
        self.last_value = response_output
        self.memory_manager.record_interaction(profile, self.state, user_input, response_output, tool_events)
        return response_output
    def _run_ai_with_tools(self, profile: ir.AIDecl, user_input: str, memory_context: dict, tool_events: list[dict]) -> str:
        max_calls = 3
        tool_results: list[dict] = []
        for _ in range(max_calls + 1):
            response = self.ai_provider.ask(
                model=profile.model,
                system_prompt=profile.system_prompt,
                user_input=user_input,
                tools=[{"name": name} for name in profile.exposed_tools],
                memory=memory_context,
                tool_results=tool_results,
            )
            if isinstance(response, AIToolCallResponse):
                if response.tool_name not in profile.exposed_tools:
                    raise Namel3ssError(f"AI requested unexposed tool '{response.tool_name}'")
                if not isinstance(response.args, dict):
                    raise Namel3ssError("Tool call args must be a dictionary")
                tool_events.append({"type": "call", "name": response.tool_name, "args": response.args})
                result = execute_tool(response.tool_name, response.args)
                tool_events.append({"type": "result", "name": response.tool_name, "result": result})
                tool_results.append({"name": response.tool_name, "result": result})
                continue
            if not isinstance(response.output, str):
                raise Namel3ssError("AI response must be a string")
            return response.output
        raise Namel3ssError("AI exceeded maximum tool calls")
    def _execute_run_agent(self, stmt: ir.RunAgentStmt) -> None:
        output, trace = self._run_agent_call(stmt.agent_name, stmt.input_expr, stmt.line, stmt.column)
        self.traces.append(trace)
        if stmt.target in self.constants:
            raise Namel3ssError(f"Cannot assign to constant '{stmt.target}'", line=stmt.line, column=stmt.column)
        self.locals[stmt.target] = output
        self.last_value = output

    def _execute_run_agents_parallel(self, stmt: ir.RunAgentsParallelStmt) -> None:
        if len(stmt.entries) > 3:
            raise Namel3ssError("Parallel agent limit exceeded")
        results: list[str] = []
        child_traces: list[dict] = []
        for entry in stmt.entries:
            output, trace = self._run_agent_call(entry.agent_name, entry.input_expr, entry.line, entry.column)
            results.append(output)
            child_traces.append(trace.__dict__ if hasattr(trace, "__dict__") else trace)
        self.locals[stmt.target] = results
        self.last_value = results
        self.traces.append({"type": "parallel_agents", "target": stmt.target, "agents": child_traces})

    def _run_agent_call(self, agent_name: str, input_expr, line: int | None, column: int | None):
        self.agent_calls += 1
        if self.agent_calls > 5:
            raise Namel3ssError("Agent call limit exceeded in flow")
        if agent_name not in self.agents:
            raise Namel3ssError(f"Unknown agent '{agent_name}'", line=line, column=column)
        agent = self.agents[agent_name]
        ai_profile = self.ai_profiles.get(agent.ai_name)
        if ai_profile is None:
            raise Namel3ssError(f"Agent '{agent.name}' references unknown AI '{agent.ai_name}'", line=line, column=column)
        user_input = self._evaluate_expression(input_expr)
        if not isinstance(user_input, str):
            raise Namel3ssError("Agent input must be a string", line=line, column=column)
        profile_override = ir.AIDecl(
            name=ai_profile.name,
            model=ai_profile.model,
            system_prompt=agent.system_prompt or ai_profile.system_prompt,
            exposed_tools=list(ai_profile.exposed_tools),
            memory=ai_profile.memory,
            line=ai_profile.line,
            column=ai_profile.column,
        )
        memory_context = self.memory_manager.recall_context(profile_override, user_input, self.state)
        tool_events: list[dict] = []
        response_output = self._run_ai_with_tools(profile_override, user_input, memory_context, tool_events)
        trace = AITrace(
            ai_name=profile_override.name,
            ai_profile_name=profile_override.name,
            agent_name=agent.name,
            model=profile_override.model,
            system_prompt=profile_override.system_prompt,
            input=user_input,
            output=response_output,
            memory=memory_context,
            tool_calls=[e for e in tool_events if e.get("type") == "call"],
            tool_results=[e for e in tool_events if e.get("type") == "result"],
        )
        self.memory_manager.record_interaction(profile_override, self.state, user_input, response_output, tool_events)
        return response_output, trace

    def _handle_find(self, stmt: ir.Find) -> None:
        schema = self._get_schema(stmt.record_name, stmt)

        def predicate(record: dict) -> bool:
            backup_locals = self.locals.copy()
            try:
                self.locals.update(record)
                result = self._evaluate_expression(stmt.predicate)
                if not isinstance(result, bool):
                    raise Namel3ssError(
                        "Find predicate must evaluate to boolean",
                        line=stmt.line,
                        column=stmt.column,
                    )
                return result
            finally:
                self.locals = backup_locals

        results = self.store.find(schema, predicate)
        result_name = f"{stmt.record_name.lower()}_results"
        self.locals[result_name] = results
        self.last_value = results

    def _get_schema(self, record_name: str, stmt: ir.Statement) -> RecordSchema:
        if record_name not in self.schemas:
            raise Namel3ssError(
                f"Unknown record '{record_name}'",
                line=stmt.line,
                column=stmt.column,
            )
        return self.schemas[record_name]

def execute_flow(
    flow: ir.Flow,
    schemas: Optional[Dict[str, RecordSchema]] = None,
    initial_state: Optional[Dict[str, object]] = None,
    input_data: Optional[Dict[str, object]] = None,
    ai_provider: Optional[AIProvider] = None,
    ai_profiles: Optional[Dict[str, ir.AIDecl]] = None,
) -> ExecutionResult:
    return Executor(
        flow,
        schemas=schemas,
        initial_state=initial_state,
        input_data=input_data,
        ai_provider=ai_provider,
        ai_profiles=ai_profiles,
    ).run()


def execute_program_flow(
    program: ir.Program,
    flow_name: str,
    *,
    state: Optional[Dict[str, object]] = None,
    input: Optional[Dict[str, object]] = None,
    store: Optional[MemoryStore] = None,
    ai_provider: Optional[AIProvider] = None,
) -> ExecutionResult:
    flow = next((f for f in program.flows if f.name == flow_name), None)
    if flow is None:
        raise Namel3ssError(f"Unknown flow '{flow_name}'")
    schemas = {schema.name: schema for schema in program.records}
    return Executor(
        flow,
        schemas=schemas,
        initial_state=state,
        input_data=input,
        store=store,
        ai_provider=ai_provider,
        ai_profiles=program.ais,
        agents=program.agents,
    ).run()
