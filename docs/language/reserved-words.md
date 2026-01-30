# Reserved words in namel3ss

- Reserved words are part of the language and UI DSL and cannot be reused as variable names.
- They keep the grammar clear, align with the UI DSL, and protect deterministic execution.

## Escaping
- Escape a reserved word by wrapping it in backticks when it must be an identifier.
- Otherwise, choose a non-reserved name with domain context.
- The canonical list is defined in `docs/language/grammar_contract.md` (reserved_keywords snapshot).

Example (unescaped fails, escaped works):
```text
let title is "Welcome"
let `title` is "Welcome"
```

To see the canonical list:
```bash
n3 reserved
```
