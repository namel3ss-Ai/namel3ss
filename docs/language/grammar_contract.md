# namel3ss Grammar Contract

> This document defines the frozen grammar and semantics of namel3ss. Changes require explicit compatibility review.

## Scope
- The rules below are authoritative for all parsers, builders, and tooling.
- Reserved words, identifiers, expressions, and match blocks follow a single canonical form.
- Static vs runtime responsibilities are fixed; any change must go through compatibility review.

## Canonical Grammar Snapshot
The JSON below is the canonical, test-locked grammar surface for keywords and grammar entry points.

<!-- CONTRACT:grammar -->
```json
{
  "expression_rules": [
    "number",
    "string",
    "boolean",
    "null",
    "latest",
    "identifier",
    "input",
    "state",
    "grouped",
    "call",
    "ask"
  ],
  "reserved_keywords": [
    "agent",
    "agents",
    "ai",
    "and",
    "app",
    "as",
    "ask",
    "at",
    "be",
    "bool",
    "boolean",
    "button",
    "call",
    "calls",
    "capabilities",
    "card",
    "catch",
    "column",
    "constant",
    "create",
    "divider",
    "each",
    "else",
    "enqueue",
    "entry",
    "equal",
    "expose",
    "false",
    "find",
    "flow",
    "for",
    "form",
    "greater",
    "have",
    "if",
    "image",
    "in",
    "input",
    "input_schema",
    "int",
    "integer",
    "is",
    "job",
    "json",
    "kind",
    "latest",
    "least",
    "length",
    "less",
    "let",
    "match",
    "memory",
    "model",
    "most",
    "must",
    "not",
    "null",
    "number",
    "or",
    "otherwise",
    "output_schema",
    "page",
    "parallel",
    "param",
    "pattern",
    "present",
    "profile",
    "provider",
    "purity",
    "record",
    "repeat",
    "require",
    "return",
    "row",
    "run",
    "save",
    "section",
    "semantic",
    "set",
    "short_term",
    "spec",
    "state",
    "str",
    "string",
    "system_prompt",
    "table",
    "text",
    "than",
    "theme",
    "theme_preference",
    "theme_tokens",
    "timeout_seconds",
    "times",
    "title",
    "to",
    "tool",
    "tools",
    "true",
    "try",
    "ui",
    "unique",
    "up",
    "when",
    "where",
    "with"
  ],
  "statement_rules": [
    "start_run",
    "plan",
    "review_parallel",
    "timeline",
    "compute_output_hash",
    "increment_metric",
    "attempt_otherwise",
    "attempt_blocked_tool",
    "verb_agent_call",
    "verb_agent_call_shorthand",
    "in_parallel",
    "clear",
    "notice",
    "log",
    "metric",
    "require_latest",
    "record_final_output",
    "record_policy_violation",
    "calc",
    "let",
    "set_theme",
    "set",
    "if",
    "return",
    "ask",
    "parallel",
    "orchestration",
    "run_agents_parallel",
    "run_agent",
    "enqueue_job",
    "tick",
    "repeat",
    "for_each",
    "match",
    "try",
    "save_with",
    "save",
    "create",
    "find",
    "update",
    "delete"
  ],
  "top_level_rules": [
    "spec",
    "contract",
    "function",
    "use",
    "capsule",
    "identity",
    "app",
    "capabilities",
    "policy",
    "packs",
    "foreign",
    "tool",
    "agent_team",
    "agent",
    "ai",
    "record",
    "flow",
    "job",
    "page",
    "ui",
    "ui_pack",
    "ui_pattern"
  ]
}
```
<!-- END_CONTRACT:grammar -->

## Lexical Rules
- Source is line-based; indentation is significant. Indentation changes emit `INDENT`/`DEDENT` tokens.
- Inconsistent indentation is a lexer error.
- Whole-line comments only: a line whose first non-space character is `#` is skipped.
- Identifiers: `[A-Za-z_][A-Za-z0-9_]*`. If the text matches a reserved word, the lexer emits the keyword token.
- Escaped identifiers: backticks (`` `name` ``) emit an escaped identifier token and must contain valid identifier chars.
- Strings: double-quoted only (`"..."`), no escape sequences. Unterminated strings are a lexer error.
- Numbers: digits with optional fractional part; unary minus is handled by the parser.
- Punctuation tokens: `:` `.` `+` `-` `*` `**` `/` `%` `=` `(` `)` `[` `]` `,`.
- Unsupported characters raise a lexer error with guidance.

## Identifiers (bare or quoted, everywhere)
- Names may be bare identifiers or quoted strings.
- Reserved words must be quoted or escaped when used as identifiers.
- Dot-qualified references use the same rule for every segment; keywords are allowed when quoted or escaped.

## Top-level Declarations (canonical order)
Parsing order is the disambiguation order; it is stable and must not change.
- `spec` declaration.
- `contract` flow/pipeline declarations.
- `define` function declarations.
- `use` module declarations.
- `capsule` declarations.
- `identity` declarations.
- `app` declaration.
- `capabilities` declaration.
- `policy` declaration.
- `packs` declaration.
- `foreign` declarations.
- `tool` declarations.
- `team` of agents declaration.
- `agent` declarations.
- `ai` declarations.
- `record` declarations.
- `flow` declarations.
- `job` declarations.
- `page` declarations.
- `ui` declarations.
- `ui_pack` declarations.
- `ui_pattern` declarations.

## Statements (canonical order)
Parsing order is the disambiguation order; it is stable and must not change.
- `start run` (start_run)
- `plan ... with` (plan)
- `review ...` (review_parallel)
- `timeline ...` (timeline)
- `compute output hash` (compute_output_hash)
- `increment metric` (increment_metric)
- `attempt ... otherwise` (attempt_otherwise)
- `attempt ... tool blocked` (attempt_blocked_tool)
- agent verb call (verb_agent_call)
- agent verb shorthand call (verb_agent_call_shorthand)
- `in parallel` (in_parallel)
- `clear` (clear)
- `notice` (notice)
- `log` (log)
- `metric` (metric)
- `require latest` (require_latest)
- `record final output` (record_final_output)
- `record policy violation` (record_policy_violation)
- `calc` (calc)
- `let` (let)
- `set theme` (set_theme)
- `set` (set)
- `if` (if)
- `return` (return)
- `ask` (ask)
- `parallel` block (parallel)
- `orchestration` block (orchestration)
- `run agents` (run_agents_parallel)
- `run agent` (run_agent)
- `enqueue job` (enqueue_job)
- `tick` (tick)
- `repeat` (repeat)
- `for each` (for_each)
- `match` (match)
- `try` (try)
- `save with` (save_with)
- `save` (save)
- `create` (create)
- `find` (find)
- `update` (update)
- `delete` (delete)

## Expressions (canonical order)
Parsing order is the disambiguation order; it is stable and must not change.
- `number` literal
- `string` literal
- `boolean` literal
- `null` literal
- `latest` expression
- identifier reference
- `input` reference
- `state.<path>` reference
- grouped expression `(...)`
- `call <tool|flow|pipeline|function>` expression
- `ask <ai>` expression

## UI Page Items (canonical order)
Parsing order is the disambiguation order; it is stable and must not change.
- `compose` (semantic grouping)
- `story`
- `number`
- `view`
- `title`
- `text`
- `upload`
- `form`
- `table`
- `list`
- `chart`
- `use ui_pack` / `use pattern`
- `chat` (container)
- `tabs` (page root only)
- `modal`
- `drawer`
- `button`
- `link`
- `section`
- `card_group`
- `card`
- `row`
- `column`
- `divider`
- `image`

Chat sub-items (`messages`, `composer`, `thinking`, `citations`, `memory`) are only valid inside a `chat` block.
Tab entries (`tab`) are only valid inside a `tabs` block.

## Expressions (existence checked only at runtime)
- Expression grammar is stable; parsing never validates runtime existence of state, identity, records, or flows.
- `state.*` paths and attribute access are accepted syntactically; missing data is a runtime or build-time semantic concern.
- Static validation may warn about undeclared paths but cannot reject syntactically valid expressions.

## Match grammar (single canonical form)
- `match <expression>:` must include a `with:` block containing `when` arms; `otherwise` is optional.
- No alternate syntaxes are permitted; absence of `with:` is a parse error.
- `when` arms use the same expression grammar; ordering and exhaustiveness are runtime semantics.

## Validation phases (parse / build / runtime)
- **Parse**: Enforces grammar and token rules only; succeeds if the source conforms to this contract.
- **Build (STATIC)**: Performs structural validation, shape checks, and emits warnings for runtime-only requirements; must not require environment, identity, secrets, or data presence.
- **Runtime (RUNTIME)**: Enforces identity, permissions, trust, capability checks, and data existence; failures here are errors, not warnings.

## Change control
- Grammar or semantic changes are breaking and require an explicit compatibility review and RFC.
- The `docs/grammar/current.md` file is a historical snapshot and not a contract.
- Contract tests (`tests/parser/test_grammar_current.py` and related grammar checks) must stay green to ship.
