# namel3ss Grammar Analysis Report

## 1. Overview
The grammar is predominantly English-first and block-structured with clear colon/indent boundaries. Property assignment via `is` and constraints via `must` are readable. A few legacy allowances and alias behaviors introduce mild drift risk. Diagnostics generally include line/column, but some messages are terse.

## 2. Grammar Shape (What Exists)
- Top-level blocks: `app:`, `record "Name":`, `page "name":`, `flow "name":`, `ai "name":`, `agent "name":`, `tool "name":` (colon + indented body).
- Naming rule in practice: declaration keywords take quoted names; record fields still allow legacy identifier-without-`field` plus optional `is`.
- Properties: `property is <value>` pattern (theme, model, system_prompt, provider, etc.).
- Statements: `let name is expr`, `set target is expr`, control flow (`if/else`, `repeat up to`, `for each`, `match/when/otherwise`, `try/catch`, `return`), AI call (`ask ai "name" with input: expr as var`), record ops (`save Record`, `find Record where ...`), agent ops, theme change (`set theme to "..."`).
- UI DSL: declarative page items (title, text, form, table, button, section, card, row, column, divider, image). Row → column constraint enforced; other containers can nest items.
- App/theme: `theme is "light|dark|system"`, optional `theme_tokens` map, `theme_preference` block (`allow_override`, `persist`).
- Constraints: `field "name" is <type> must be present|unique|greater than|less than|match pattern|have length at least/at most`.

## 3. Strengths
- English-like `is`/`must` keeps readability high.
- Indentation + colons provide strict block boundaries.
- Closed sets for theme values and preference flags reduce ambiguity.
- Declarative UI blocks disallow imperative statements, keeping intent clear.
- Line/column diagnostics are common and helpful.

## 4. Inconsistencies & Risks
- Record fields: parser accepts both canonical `field "x" is type` and legacy `name type` without `field` or `is`, inviting drift.
- Type vocabulary: canonical should be `text/number/boolean(/json)`, but lexer/grammar still accept `string`/`int`/`bool` aliases; `text` is a UI keyword, not a lexer type, which can confuse. Normalization is minimal.
- Constraint phrasing: parser enforces `have length at least/at most`; formatter history showed variants (`length min`) leading to regressions.
- Theme tokens: parser accepts arbitrary strings; validation occurs later, allowing invalid values until lint.
- Users often expect object literal saves (`save Record { ... }`), but only state-based `save Record` is supported, causing parse errors on `{`.

## 5. English-First Evaluation
- Natural: `title is "Hello"`, `field "email" is string must be present`, `button "Save": calls flow "save_user"`.
- Less natural: `int/boolean/json` are programmer terms; `pattern` expects regex; `length at least` is formal but clear.
- Confusion points: optional `field` keyword, missing `is` in legacy fields, `text` vs `string`, and forbidden `{}` in saves.

## 6. Type System Findings
- Canonical vocabulary to converge on: `text`, `number`, `boolean` (and `json` if supported today).
- Aliases exist today (parser accepts `string`/`int`/`bool`), but they are not canonical and create drift risk.
- Accepted lexer types: string, int, number, boolean, json (mapped to type names; no further normalization).
- AST stores mapped type names; IR carries them unchanged. Formatter/lint aim for `field "x" is <type> must ...` but parser permissiveness remains.

## 7. Strictness Recommendations (No Code Yet)
- Canonicalize record fields to `field "name" is <type>` only; deprecate identifier-only forms.
- Keep a single type vocabulary (string/int/number/boolean/json); avoid new synonyms without normalization.
- Enforce constraint wording consistently (`must be present|unique|greater than|less than|match pattern|have length at least/at most`); formatter/lint should reject variants.
- Validate theme tokens/values early against closed enums to reduce free-form strings.
- Preserve declarative-only pages and English comparison phrases.

## 8. What Should NOT Change
- Block structure with quoted names and indented bodies.
- `property is value` pattern and `must ...` constraints.
- Declarative UI surface and row→column nesting rule.
- Closed theme value sets and preference flags.
- Line/column-rich diagnostics for fast debugging.
