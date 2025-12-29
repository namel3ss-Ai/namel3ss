from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

from namel3ss.ast.modules import UseDecl
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.test_runner.types import (
    ExpectErrorContainsStep,
    ExpectValueContainsStep,
    ExpectValueIsStep,
    RunFlowStep,
    TestCase,
    TestFile,
)


USE_MODULE_RE = re.compile(
    r'^use\s+module\s+"(?P<module>[^"]+)"\s+as\s+(?P<alias>[A-Za-z_][A-Za-z0-9_]*)\s*$'
)
USE_RE = re.compile(r'^use\s+"(?P<module>[^"]+)"\s+as\s+(?P<alias>[A-Za-z_][A-Za-z0-9_]*)\s*$')
TEST_RE = re.compile(r'^test\s+"(?P<name>[^"]+)"\s*:\s*$')
RUN_RE = re.compile(
    r'^run\s+flow\s+"(?P<flow>[^"]+)"\s+with\s+input:\s+(?P<input>.+?)\s+as\s+(?P<target>[A-Za-z_][A-Za-z0-9_]*)\s*$'
)
EXPECT_VALUE_IS_RE = re.compile(r"^expect\s+value\s+is\s+(?P<literal>.+)$")
EXPECT_VALUE_CONTAINS_RE = re.compile(r'^expect\s+value\s+contains\s+"(?P<text>[^"]*)"\s*$')
EXPECT_ERROR_CONTAINS_RE = re.compile(r'^expect\s+error\s+contains\s+"(?P<text>[^"]*)"\s*$')


def parse_test_file(path: Path) -> TestFile:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    uses: list[UseDecl] = []
    tests: list[TestCase] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        if _is_blank(raw):
            i += 1
            continue
        indent = _leading_spaces(raw)
        line = raw.strip()
        if line.startswith("#"):
            i += 1
            continue
        module_match = USE_MODULE_RE.match(line)
        use_match = module_match or USE_RE.match(line)
        if use_match:
            if indent != 0:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Use statement must be at top level in test files.",
                        why="Indented use statements are not allowed inside tests.",
                        fix="Move the use statement to the top of the file.",
                        example='use \"inventory\" as inv',
                    ),
                    line=i + 1,
                    column=indent + 1,
                )
            uses.append(
                UseDecl(
                    module=use_match.group("module"),
                    alias=use_match.group("alias"),
                    module_path=module_match.group("module") if module_match else None,
                    line=i + 1,
                    column=indent + 1,
                )
            )
            i += 1
            continue
        test_match = TEST_RE.match(line)
        if test_match:
            if indent != 0:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Test declarations must be at top level.",
                        why="Tests cannot be nested inside other blocks.",
                        fix='Move the test block to the top level.',
                        example='test \"calculates total\":',
                    ),
                    line=i + 1,
                    column=indent + 1,
                )
            test_name = test_match.group("name")
            test_line = i + 1
            i += 1
            steps: list = []
            block_indent = None
            while i < len(lines):
                raw = lines[i]
                if _is_blank(raw):
                    i += 1
                    continue
                indent = _leading_spaces(raw)
                if indent <= 0:
                    break
                if block_indent is None:
                    block_indent = indent
                if indent != block_indent:
                    raise Namel3ssError(
                        build_guidance_message(
                            what="Inconsistent indentation in test block.",
                            why="All test steps must use the same indentation.",
                            fix="Align test steps to the same indent level.",
                            example='  run flow \"calc\" with input: {} as result',
                        ),
                        line=i + 1,
                        column=indent + 1,
                    )
                step_line = raw.strip()
                steps.append(_parse_step(step_line, line=i + 1, column=indent + 1))
                i += 1
            if not steps:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Test block has no steps.",
                        why="Each test must run a flow and include expectations.",
                        fix="Add at least one run/expect step.",
                        example='run flow \"calc\" with input: {} as result',
                    ),
                    line=test_line,
                    column=1,
                )
            tests.append(TestCase(name=test_name, steps=steps, line=test_line, column=1))
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Unexpected line in test file.",
                why="Test files only support use statements and test blocks.",
                fix='Start with `test \"name\":` or a `use` statement.',
                example='test \"smoke\":',
            ),
            line=i + 1,
            column=indent + 1,
        )
    return TestFile(path=path.as_posix(), uses=uses, tests=tests)


def _parse_step(text: str, *, line: int, column: int):
    run_match = RUN_RE.match(text)
    if run_match:
        input_text = run_match.group("input")
        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError as err:
            raise Namel3ssError(
                build_guidance_message(
                    what="Test input payload is not valid JSON.",
                    why=f"JSON parsing failed: {err.msg}.",
                    fix="Provide a valid JSON object for input.",
                    example='run flow \"calc\" with input: {\"values\": {\"qty\": 2}} as result',
                ),
                line=line,
                column=column,
            ) from err
        if not isinstance(input_data, dict):
            raise Namel3ssError(
                build_guidance_message(
                    what="Test input payload must be a JSON object.",
                    why="Flows expect a dictionary of inputs.",
                    fix="Wrap input values in an object.",
                    example='run flow \"calc\" with input: {\"qty\": 2} as result',
                ),
                line=line,
                column=column,
            )
        return RunFlowStep(
            flow_name=run_match.group("flow"),
            input_data=input_data,
            target=run_match.group("target"),
            line=line,
            column=column,
        )
    expect_value_match = EXPECT_VALUE_IS_RE.match(text)
    if expect_value_match:
        literal = _parse_literal(expect_value_match.group("literal").strip(), line=line, column=column)
        return ExpectValueIsStep(expected=literal, line=line, column=column)
    expect_contains_match = EXPECT_VALUE_CONTAINS_RE.match(text)
    if expect_contains_match:
        return ExpectValueContainsStep(expected=expect_contains_match.group("text"), line=line, column=column)
    expect_error_match = EXPECT_ERROR_CONTAINS_RE.match(text)
    if expect_error_match:
        return ExpectErrorContainsStep(expected=expect_error_match.group("text"), line=line, column=column)
    raise Namel3ssError(
        build_guidance_message(
            what="Unknown test step.",
            why="Supported steps are run flow, expect value is/contains, and expect error contains.",
            fix="Use a supported test step syntax.",
            example='expect value contains \"ok\"',
        ),
        line=line,
        column=column,
    )


def _parse_literal(text: str, *, line: int, column: int) -> object:
    lower = text.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower == "null":
        return None
    if text.startswith('"') and text.endswith('"'):
        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            raise Namel3ssError(
                build_guidance_message(
                    what="String literal is invalid JSON.",
                    why=f"JSON parsing failed: {err.msg}.",
                    fix="Use a valid quoted string.",
                    example='"ok"',
                ),
                line=line,
                column=column,
            ) from err
    try:
        return Decimal(text)
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Expected a literal value.",
                why="Allowed literals are numbers, strings, true/false, or null.",
                fix="Provide a supported literal.",
                example='expect value is 10.5',
            ),
            line=line,
            column=column,
        ) from err


def _leading_spaces(text: str) -> int:
    count = 0
    for ch in text:
        if ch == " ":
            count += 1
        else:
            break
    return count


def _is_blank(text: str) -> bool:
    return text.strip() == ""
