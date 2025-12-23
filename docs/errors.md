# Error Reference

## Categories
- **lexer_error**: invalid characters or tokens during lexing (e.g., `Unexpected character '@'`).
- **parser_error**: syntax issues while building the AST (e.g., `Expected IDENT, got EOF`).
- **validation_error**: schema or data validation failures (records/forms), often structured.
- **engine_error**: execution-time issues (bad types, unknown variables, limits exceeded).
- **ai_error**: AI-related failures (unknown AI profile, tool misuse, call limits).
- **tool_error**: problems invoking tools (bad args, unexposed tool).

## Rendering with context
- Use `errors.render.format_error(err, source)` to include source lines and a caret.
- Output includes the original error message plus:
  - Source line (if `err.line` and source provided)
  - Caret (`^`) under the column (clamped to end-of-line if needed)

Example:
```
[line 2, col 5] Expected identifier
let x is
    ^
```

## Structured validation errors (forms/records)
- Shape: list of `{ "field": <name>, "code": <code>, "message": <detail> }`.
- Codes: `present`, `unique`, `type`, `gt`, `lt`, `min_length`, `max_length`, `pattern`.
- Raised by `submit_form` and record validation paths when input fails schema checks.

## Examples by category
- lexer_error: `Unexpected character '@'`
- parser_error: `Expected ':' after condition`
- validation_error: `Field 'age' must be present`
- engine_error: `Cannot set undeclared variable 'x'`
- ai_error: `Unknown AI 'assistant'`
- tool_error: `AI requested unexposed tool 'search'`

### Parser migration: buttons are block-only
- Rejected:
  ```
  button "Run" calls flow "demo"
  ```
- Correct:
  ```
  button "Run":
    calls flow "demo"
  ```
- Example error: `Buttons must use a block. Use: button "Run": NEWLINE indent calls flow "demo"`
