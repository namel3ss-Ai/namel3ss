# Grammar and Type System Modernisation

This phase adds a formal grammar source file, generated parser metadata, richer type expressions, canonical AST output, and schema tooling.

## Single grammar source

- Grammar file: `spec/grammar/namel3ss.grammar`
- Generator script: `tools/generate_parser.py`
- Generated snapshot: `src/namel3ss/parser/generated/grammar_snapshot.py`

The grammar file is the source of truth. Run:

```bash
python tools/generate_parser.py
```

to refresh parser metadata after grammar edits.

## Parser transition

- Parser entry now goes through the generated parser facade only.
- Legacy parser override flags are removed.

## Type expressions

The parser now accepts:

- Primitive types: `text`, `number`, `boolean`, `json`, `null`
- Generic types: `list<text>`, `map<text, number>`
- Union types: `number | text`
- Optional types: `text | null`

Legacy aliases still normalize:

- `string` to `text`
- `int` to `number`
- `bool` to `boolean`

## New CLI commands

- `n3 ast dump [app.ai] --json`
- `n3 type check [app.ai] --json`
- `n3 schema infer [app.ai] --json`
- `n3 schema migrate [app.ai] --json`

## Deterministic outputs

- `n3 ast dump` writes canonical CIR JSON.
- `n3 ast dump` also includes `representation_schema: "program_representation.v1"` for the compiler-facing contract.
- `n3 type check` emits stable, sorted diagnostics.
- `n3 schema infer` and `n3 schema migrate` write deterministic artifacts to:
  - `.namel3ss/schema_infer.json`
  - `.namel3ss/schema_migrate.json`
