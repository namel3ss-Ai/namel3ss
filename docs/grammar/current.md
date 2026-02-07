# Current Grammar (Parser Snapshot)
# This file is a historical snapshot of parser behavior. It is not the authoritative contract; see docs/language/grammar_contract.md.

Derived from source files under `src/namel3ss/lexer` and `src/namel3ss/parser`.

## Docs and SDKs

This phase adds optional grouping delimiters (`[]`, `{}`) for selected list and compact block contexts. Use the CLI to generate docs and SDKs from existing routes:
- `n3 docs` for the local docs portal
- `n3 sdk generate --lang python|typescript|go|rust --out-dir sdk`
- `n3 sdk postman --out postman.json`
- `n3 metrics` and `n3 prompts list` for AI metadata
- `n3 conventions check` and `n3 formats list` for route conventions
- `n3 plugin new` for plugin scaffolding

## Lexer Summary
- Identifiers: `[A-Za-z_][A-Za-z0-9_]*`; if the text matches a reserved word, it is emitted as that keyword token (not `IDENT`).
- Escaped identifiers: `` `name` ``; backtick-escaped identifiers are emitted as `IDENT_ESCAPED` with the unescaped text value.
- Strings: double-quoted only (`"..."`), no escape handling; unterminated strings are a lexer error.
- Numbers: digits with optional fractional part; minus is its own token (unary minus is handled by the parser).
- Comments: whole-line comments only; a line whose first non-space character is `#` is skipped.
- Indentation: significant; indentation changes emit `INDENT`/`DEDENT`, inconsistent spacing raises a lexer error.
- Punctuation tokens: `:` `.` `+` `-` `*` `**` `/` `%` `=` `(` `)` `[` `]` `{` `}` `,` `<` `>`.

## Reserved Words (KEYWORDS)
```
flow
page
app
spec
ai
ask
with
input
input_schema
output_schema
as
provider
tools
expose
tool
call
kind
entry
purity
timeout_seconds
memory
short_term
semantic
profile
agent
agents
parallel
run
model
system_prompt
title
text
theme
theme_tokens
theme_preference
ui
form
table
button
section
card
row
column
divider
image
calls
record
save
create
find
where
let
latest
set
require
return
repeat
up
to
times
for
each
in
match
when
otherwise
try
catch
if
else
is
greater
less
equal
than
and
or
not
state
constant
true
false
null
string
str
int
integer
number
boolean
bool
json
must
be
present
unique
pattern
have
length
at
least
most
capabilities
job
enqueue
```

## Parser Entry Points
- `namel3ss.parser.core.parse` and `Parser.parse` (lexer + parser; lowers sugar by default).
- `namel3ss.parser.parse_program.parse_program` (program-level entry used by `Parser`).

## Grammar Surfaces

Top-level declarations (`src/namel3ss/parser/grammar_table.py`):
- `spec`, `define` (function), `use`, `capsule`, `identity`, `app`, `capabilities`, `policy`, `packs`, `foreign`, `tool`,
  `agent`, `team of agents`, `ai`, `record`, `crud`, `prompt`, `llm_call`, `rag`, `classification`, `summarise`,
  `route`, `flow`, `job`, `page`, `ui`, `ui_pack`.

Optional grouping sugar:
- Bracket lists: `labels: [billing, technical]`, `sources: [docs, kb]`, `capabilities: [http, jobs]`, `packs: ["builtin.text"]`, `only: [functions, tools]`.
- Braced compact blocks: `record "User": { id number, name text }`, `fields: { id is text, status is text }`, `parameters: { heading is text }`.
- Grouped forms normalize to the same AST as equivalent indented forms.
- Commas are required between grouped entries.
- Nested grouping is rejected.
- Grouped forms are single-line only in parser input; multi-line grouping must use indentation form.

Statements (`src/namel3ss/parser/grammar_table.py`):
- `start`, `plan`, `review`, `timeline`, `compute`, `increment`, `attempt` (two forms), agent verb calls,
  `in`, `clear`, `notice`, `require`, `record` (final output/policy violation), `calc`, `let`, `set`,
  `if`, `return`, `ask`, `parallel`, `run agent(s)`, `repeat`, `for each`, `match`, `try`, `save`,
  `create`, `find`, `update`, `delete`.

UI page items (`src/namel3ss/parser/decl/page_items.py`):
- `title`, `text`, `form`, `table`, `list`, `chart`, `use ui_pack`, `chat` (messages/composer/thinking/citations/memory),
  `tabs`/`tab`/`default`, `modal`, `drawer`, `button`, `link`, `section`, `card_group`, `card`, `row`, `column`, `divider`, `image`.

Expressions (`src/namel3ss/parser/grammar_table.py` and `src/namel3ss/parser/expr`):
- literals (`number`, `string`, `boolean`, `null`), `latest`, `input`, `state.<path>`, identifier/attribute access,
  grouped `(...)`, `call ...`, `ask ...`.

Reference names (`src/namel3ss/parser/core/helpers.py`):
- Record/field/flow/tool names are either strings or dot-qualified identifiers.
- Dot-qualified reference names require `IDENT` segments; reserved words must be quoted or escaped with backticks.
- Dot-qualified attribute access and state paths use `read_attr_name`, which accepts keyword tokens as segments.

## Parse Acceptance Snippets

| Snippet | Expected parse result | Module responsible |
| --- | --- | --- |
| `flow "demo":<br>  match state.status:<br>    with:<br>      when "ok":<br>        return "ok"` | Parses successfully. | `src/namel3ss/parser/stmt/match.py` |
| `flow "demo":<br>  match state.status:<br>    when "ok":<br>      return "ok"` | Fails with `Expected 'with' inside match`. | `src/namel3ss/parser/stmt/match.py` |
| `flow "demo":<br>  update "Order" where id is 1 set:<br>    status is "done"<br>    "title" is "Ready"` | Parses successfully; field names accept bare identifiers and quoted strings. | `src/namel3ss/parser/stmt/update.py`, `src/namel3ss/parser/core/helpers.py` |
| `page "home":<br>  title is "Welcome"` | Parses successfully; `title` is a reserved word used as a UI key. | `src/namel3ss/parser/decl/page_items.py` |
| `flow "demo":<br>  return state.missing.value` | Parses successfully; state path existence is not validated here (runtime resolution raises on missing paths). | `src/namel3ss/parser/expr/statepath.py`, `src/namel3ss/runtime/executor/expr/core.py` |
| `flow "demo":<br>  find "Order" where id is 1` | Parses successfully; record references accept quoted names. | `src/namel3ss/parser/stmt/find.py`, `src/namel3ss/parser/core/helpers.py` |
| `page "home":<br>  button "Save":<br>    calls flow "demo"<br>  button "Save":<br>    calls flow "demo"` | Parses successfully; duplicate UI action ids are detected during manifest build. | `src/namel3ss/ui/manifest/elements.py`, `src/namel3ss/ui/manifest/page.py` |
