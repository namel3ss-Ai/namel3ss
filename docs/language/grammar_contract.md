# namel3ss Grammar and Behavior Contract

This document defines the frozen grammar and semantics of namel3ss.
Changes require explicit compatibility review.
This document is the authoritative contract for namel3ss grammar and behavior. It freezes the language surface and determinism guarantees. Any conflict between this document and other docs, tests, or code is a bug.

## Docs and SDK tooling
- This phase adds optional grouping delimiters for selected list and compact block contexts.
- API docs, SDKs, metrics, and prompt tooling are generated from existing route, prompt, and AI flow declarations.
- Use `n3 docs`, `n3 sdk`, `n3 metrics`, and `n3 prompts list` to access these features.

## Authority and scope
- This contract is normative for parsers, validators, the runtime, and the Studio renderer.
- Only the forms shown here are allowed. Variants, aliases, and alternate spellings are forbidden.
- This contract documents current behavior only. It does not propose new features.

## Determinism guarantees
- Same program + same inputs → same outputs.
- UI manifests are fully replayable and deterministic.
- Action identifiers are deterministic and stable for the same program.
- Evaluation order is stable and defined by source order or by a documented deterministic order.
- State changes occur only through explicit statements.
- No timestamps, randomness, environment dependence, or hidden state are allowed in language semantics.

## Canonical grammar surface

### Optional grouping delimiters
- Bracketed list form is allowed where the grammar already expects flat lists: `labels`, `sources`, `capabilities`, `packs`, and `use ... only/allow override`.
- Braced compact block form is allowed for record field groups and pattern `parameters`.
- These forms are syntactic sugar only. They normalize to the same AST as the equivalent indented form.
- Entries inside `[]` and `{}` are comma-separated and preserve source order.
- Nested grouping (`[]` inside `{}` or `{}` inside `[]`) is rejected.
- Missing commas inside grouped forms are parse-time errors.
- Grouped forms are single-line only in parser input; multi-line grouped forms must be rewritten to indentation form.
- Mixing indentation and grouping delimiters in the same block is rejected.

### Top-level declarations (allowed)
The only allowed top-level declarations are:
- `spec`
- `define function`
- `contract`
- `use`
- `capsule`
- `identity`
- `app`
- `capabilities`
- `policy`
- `packs`
- `foreign`
- `tool`
- `team of agents`
- `agent`
- `ai`
- `record`
- `crud`
- `prompt`
- `llm_call`
- `rag`
- `classification`
- `summarise`
- `route`
- `flow`
- `job`
- `page`
- `ui`
- `ui_pack`
- `pattern`

Canonical examples:
```
spec is "1.0"

app:
  theme is "light"

ui:
  theme is "light"

capabilities:
  http
  jobs

policy
  allow ingestion.run

packs:
  "builtin.text"

identity "user":
  subject is text

team of agents
  "planner"
  "reviewer"

ai "assistant":
  model is "gpt-4o"

agent "planner":
  ai is "assistant"

tool "lookup":
  implemented using python
  input:
    query is text
  output:
    result is text

foreign python function "calculate":
  input:
    amount is number
  output is number

record "User":
  name text
  email text must be unique

crud "User"

prompt "summary_prompt":
  version is "1.0.0"
  text is "Summarise the input."

llm_call "summarise":
  model is "gpt-4"
  prompt is "summary_prompt"
  output is text

flow "init":
  return "ok"

route "list_users":
  path is "/api/users"
  method is "GET"
  request:
    page is number
  response:
    users is list<User>
    next_page is number
  flow is "get_users"

job "nightly":
  return "ok"

page "home":
  title is "Home"

ui_pack "core":
  version is "1.0"
  fragment "banner":
    title is "Hello"

pattern "Empty State":
  parameters:
    heading is text
  title is param.heading

define function "slug":
  input:
    value is text
  output:
    result is text
  return value

contract flow "start":
  input:
    name is text
  output:
    result is text

use "inventory" as inv
```

### Identifiers
- Identifiers are bare names or quoted strings.
- Reserved words are not identifiers unless escaped with backticks.
- The reserved word list is fixed in `docs/language/reserved-words.md`.
- Dot-qualified names use the same identifier rules for each segment.

### Expressions
- Literals are text, number, boolean, or null.
- State paths use `state.<path>` with dot notation.
- Expression syntax is fixed; no new operators or forms are allowed.

### Records
Canonical form:
```
record "User":
  name text
  email text must be unique
```

Equivalent compact form:
```
record "User": { name text, email text must be unique }
```

### Flows and statements
Canonical forms:
```
flow "demo":
  let value is 1
  set state.count to value
  if state.ready:
    return "ok"
  match state.status:
    with:
      when "ok":
        return "ok"
      otherwise:
        return "no"
  repeat up to 3 times:
    return "done"
  for each item in state.items:
    return item
  order state.items by score from highest to lowest
  keep first 5 items
  try:
    return "ok"
  catch:
    return "error"
  save "User"
  create "User" with state.user as user
  find "User" where email is "a@b.com"
  update "User" where id is 1 set:
    status is "ready"
  delete "User" where id is 1

flow "summarise":
  ai:
    model is "gpt-4"
    prompt is "Summarise the input."
  return "ok"
```

### Routes
Routes require both request and response blocks.
Canonical form:
```
route "get_user":
  path is "/api/users/{id}"
  method is "GET"
  parameters:
    id is number
  request:
    id is number
  response:
    result is User
  flow is "get_user"
```

### CRUD generator
Canonical form:
```
record "User":
  id number
  name text

crud "User"
```
Crud is a single line and has no colon.

### Prompt templates
Canonical form:
```
prompt "summary_prompt":
  version is "1.0.0"
  text is "Summarise the input."
  description is "Short summary."
```

### AI flow types
Canonical forms:
```
llm_call "summarise":
  model is "gpt-4"
  prompt is "summary_prompt"
  output is text

classification "tag_message":
  model is "gpt-4"
  prompt is "Tag the message."
  labels:
    billing
    technical
    general
  output is text

rag "answer_question":
  model is "gpt-4"
  prompt is "Answer the question."
  sources:
    documents
    memory
  output is text
```

### Pages and UI
Canonical forms:
```
page "home":
  title is "Home"
  text is "Welcome"
  button "Run":
    calls flow "demo"
  link "Settings" to page "settings"

ui:
  pages:
    active page:
      is "home" only when state.page is "home"
```

UI elements and their canonical spellings are frozen in `docs/ui-dsl.md`. Any conflict between this contract and `docs/ui-dsl.md` is a bug.

## Allowed vs forbidden rules
Allowed:
- Only the keywords and forms listed in this contract.
- Equality-only comparisons in grammar-limited surfaces that require `is`.
- Dot-qualified state paths with `state.<path>`.

Forbidden:
- Alternate spellings or aliases for any keyword.
- One-line button syntax (`button "Run" calls flow "demo"`).
- Match blocks without `with:`.
- Implicit defaults that change semantics.
- Grammar extensions outside this contract.
- UI or flow syntax that introduces expression logic where the grammar does not allow it.

## Stability and breaking-change policy
- Any change to grammar, reserved words, or determinism guarantees is a breaking change.
- The following are frozen: grammar keywords, canonical spellings, determinism guarantees, and evaluation order rules.
- Allowed changes are limited to clarifying documentation and error messages that do not change behavior.
- Any breaking change requires an RFC and a contract amendment before code changes.
- Backward compatibility policy is fixed in `docs/language/backward_compatibility.md`.

## Contribution rules
- Grammar expansion is rejected by default.
- New syntax requires an explicit contract amendment and an approved RFC.
- Refactors must not change observable behavior.
- Docs, tests, and code must agree with this contract.
- Contract tests must remain green for any change to ship.
- Contributions that touch grammar or validation must cite this contract in the change description.
