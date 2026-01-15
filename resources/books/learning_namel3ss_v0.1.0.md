# Learning namel3ss 0.1.0a7 — The Definitive Guide

## Preface

Welcome to Learning namel3ss 0.1.0a7, your comprehensive guide to namel3ss (pronounced nameless), the world’s first English‑first, AI‑native, full‑stack programming language, built from the ground up to support AI. namel3ss lets you build real applications by describing your intent in clear, structured English. Instead of juggling multiple languages, frameworks, prompts and orchestration libraries, you define your entire app in a single .ai file. namel3ss then compiles it into a validated intermediate representation (IR) and runs it in a deterministic engine where AI boundaries are explicit and inspectable.

As you’ll see, namel3ss is a fundamentally new way to build software. Throughout this guide you will learn the language grammar, explore its full‑stack capabilities, write flows, define records, create pages, integrate AI, orchestrate multiple agents, and work with the CLI and Studio tools. This book also defines every term used in the language and its engine.

This book covers namel3ss version 0.1.0a7. Future versions may introduce new features, but the core concepts you learn here will remain valuable.

## Part I: Introduction to namel3ss

### What is namel3ss?

namel3ss is an English‑first DSL (domain‑specific language) designed to build full‑stack, AI‑native applications by describing intent in structured English. The language allows you to define:

- Applications — the overarching programs consisting of flows, records, pages, AI profiles, tools and agents.
- Data models (records) — declarative schemas for storing data with built‑in validation rules.
- Backend logic (flows) — procedural sequences of statements that manipulate state, call AI profiles, run agents, save or load records and control program flow.
- User interfaces (pages) — declarative UIs containing titles, text, forms, tables and buttons that connect to your flows and records.
- AI behaviour — profiles describing models, memory, tools and system prompts, and statements ( ask ai ) to call them.
- Multi‑agent orchestration — structures for running multiple agents sequentially or in parallel, with guardrails and tracing.
- Validation and explainable errors — comprehensive compile‑time and engine validation with human‑friendly error messages.

Everything lives in a single .ai file that reads like a well‑structured specification. namel3ss is to the AI era what Python was to the web era — a language that makes building complex systems accessible to many.

### Vision and Philosophy

namel3ss is built on a few key principles:

- English‑first — The language uses plain English keywords and statements. You shouldn’t need to learn obscure symbols to express logic.
- AI is explicit, inspectable and bounded — AI calls, memory and tool usage are never hidden. You always see what’s happening, and the system enforces limits on calls to prevent runaway behaviour.
- Deterministic engine — The only non‑deterministic component is the AI model itself. Everything else is fully deterministic, so you can reason about state, loops and branches without surprises.
- Full‑stack in one language — namel3ss covers backend logic, data modelling, user interfaces and AI integration in one coherent DSL. There is no need to switch languages or coordinate between layers.
- Strong validation — Mistakes are caught early. The compiler checks grammar, naming, references and types; the engine validates data and returns structured errors; the linter warns about violations of best practices.
- Tooling — A robust CLI, formatter, linter and Studio provide professional developer workflows. You can parse, validate, run, format, lint, inspect and even visually edit your code safely.

### How namel3ss differs from other approaches

Traditional software development uses different languages and frameworks for backend, frontend and AI. Prompt engineering happens in ad‑hoc strings and orchestration is handled by separate libraries. By contrast, namel3ss combines everything into one environment. There is no hidden logic or magic functions. AI profiles, memory, tools and agent calls are just part of your structured program. This eliminates the need for glue code and reduces cognitive load.

## Part II: Getting Started

### Requirements

To run namel3ss, you need Python 3.10 or newer. namel3ss is installed via pip :

```
pip install namel3ss
```

After installation, a command‑line tool n3 becomes available. The CLI is English‑ish and file‑centric. It supports actions like checking your code, running flows, inspecting the UI manifest, formatting code, linting, listing available actions, scaffolding new projects and launching the Studio.

### Your first program

Create a file named hello.ai with the following content:

```
record "Greeting":
 field "message" is text present

page "home":
 title is "Hello"
 text is "This is your first namel3ss app"
 form is "Greeting"
 table is "Greeting"
 button "Seed":
  calls flow "seed_greetings"

flow "seed_greetings":
 save Greeting {
  message is "Welcome to namel3ss!"
 }
 return "Seeded"
```

This simple program defines a record Greeting , a page with a form and table for that record, and a flow seed_greetings that populates the store with one record. To run it:

```
n3 hello.ai
```

Since there is only one flow, the CLI automatically runs seed_greetings and prints a JSON response including the updated state and traces. You can inspect the user interface with:

```
n3 hello.ai ui
```

And see the list of actions with:

```
n3 hello.ai actions
```

Finally, to interact visually, launch the Studio:

```
n3 hello.ai studio
```

The Studio opens a local web UI where you can view pages, see actions, execute them, inspect state and traces, and make safe edits.

### Creating new projects with templates

To scaffold a new project quickly, use the n3 new command. For example, to create a starter app:

```
n3 new starter my_app
cd my_app
n3 app.ai studio
```

The project directory contains an app.ai file and a README.md with instructions. The starter template includes a minimal record and page. The demo template shows a small AI flow with an explicit boundary.

### Running flows, UI and actions

Use the CLI subcommands:

- `n3 <file>.ai` — Run the program. If multiple flows exist, specify one via `flow "name"` after the file.
- `n3 <file>.ai check` — Parse and lower the program; print OK on success or a formatted error on failure.
- `n3 <file>.ai ui` — Print the UI manifest as JSON.
- `n3 <file>.ai actions` — List all action IDs, types and details.
- `n3 <file>.ai <action_id> '{…}'` — Execute a specific action with optional JSON payload.
- `n3 <file>.ai format` — Format the source in place; `format check` to check without writing.
- `n3 <file>.ai lint` — Run linter; `lint check` exits non‑zero if findings exist.
- `n3 <file>.ai studio` — Launch the visual Studio.

## Part III: Project Structure

A typical namel3ss project contains:

```
my_app/
 app.ai   # Main program
 .env     # Optional local environment variables (ignored by Git)
 README.md
```

Large codebases may have multiple .ai files, each under 500 LOC. The CI checks line limits and single responsibility. Test files mirror the source structure in a tests/ directory (e.g. tests/lexer/test_tokens.py ).

### Templates

Packaged templates live under src/namel3ss/templates/ for starter and demo. When scaffolding via n3 new, these templates are copied into your project and placeholders like {{PROJECT_NAME}} are replaced. Each template contains a .gitignore that ignores .env, so you can place API keys locally without committing them.

### Config and Secrets

Provider configuration and secrets live outside your .ai file. Use a .env file next to app.ai or export environment variables. For example, to use OpenAI, create .env with:

```
OPENAI_API_KEY=sk-xxxxxx
```

The .ai file refers to this key via env "OPENAI_API_KEY" in the AI profile. The engine loads .env automatically and falls back to ~/.namel3ss/config.json . Real environment variables take precedence over values in .env .

## Part IV: Language Grammar

namel3ss uses clear, declarative constructs and statements. Understanding the grammar is key to mastering the language.

### Declarations

Declarations introduce top‑level entities. They never use the word is .

- `flow "name":` — Defines a backend logic unit.
- `record "Name":` — Declares a data model with fields and constraints.
- `page "name":` — Declares a user interface page.
- `ai "name":` — Defines an AI profile.
- `agent "name":` — Declares an agent for multi‑agent orchestration.
- `tool "name":` — Declares an external tool (rarely used directly).

Each declaration uses a colon to start its block and is followed by indented properties or statements. For example:

```
record "User":
 field "email" is text present unique pattern "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"
 field "name" is text present

flow "create_user":
 save User {
  email is input.email
  name is input.name
 }
 return "User created"
```

### Properties inside blocks

Within a block, properties use the is keyword to assign values. This applies to AI profiles, agent profiles, page items and record fields. For example:

```
ai "assistant":
 provider is "ollama"
 model is "llama3.1"
 system_prompt is "You are helpful."
 memory:
  short_term is 10
  semantic is true
  profile is true
 tools:
  expose "echo"
```

The pattern property is value makes the file easy to read. The grammar never uses is in declarations; that is reserved for property assignment.

### Variables and Constants

Variables hold values in flows and are defined with let or set . Constants are immutable after assignment.

```
let count is 0
let VAT is 0.21 constant
set count is count + 1
```

- let — Creates a new variable.
- set — Mutates an existing variable.
- constant — Optional keyword that marks the variable as immutable.

Variables can hold numbers, strings, booleans, lists or objects. They can also refer to state paths (more on this later).

### Expressions

Expressions appear on the right side of is in assignments and comparisons. They can be:

- Literals — Numbers ( 10 , 3.14 ), strings ( "hello" ), booleans ( true , false ), null ( null ).
- Variable references — The name of a previously declared variable.
- State paths — Paths into the program state, such as input.name or state.user.email .
- Operators — + , - , * , / , % for arithmetic; and , or , not for boolean logic; comparisons ( is greater than , is less than , is equal to , is paid shorthand).
- Unary operations — not x , -x .
- List and object literals can be written using braces:

```
let fruits is ["apple", "banana", "pear"]
let person is {
 name is "Alice"
 age is 30
}
```

### Control Flow Statements

namel3ss provides several control flow constructs:

- if / else — Branches based on a condition.

```
if x is greater than 10:
 set result is "big"
else:
 set result is "small"
```

- repeat up to — Loops up to a given integer limit.

```
repeat up to 5:
 set sum is sum + 1
```

- for each — Iterate over elements in a list or collection.

```
for each item in list:
 save Record {
  value is item
 }
```

- match / when / otherwise — Pattern matching on values.

```
match status:
 when "pending":
  set message is "Pending"
 when "complete":
  set message is "Done"
 otherwise:
  set message is "Unknown"
```

- try / catch — Handle engine errors gracefully.

```
try:
 save Record {
  field is value
 }
catch error:
 return error
```

- return — Exits a flow and returns a value.

### Page Grammar

Pages are declarative. They cannot contain let , set , if , match or other imperative constructs. The canonical page grammar is:

```
page "home":
 title is "Welcome"
 text is "Hello"
 form is "RecordName"
 table is "RecordName"
 button "Label":
  calls flow "flow_name"
```

Pages support the following items (each optional):

- title — A heading.
- text — A paragraph of text.
- form — A form bound to a record; auto‑generates fields and validation.
- table — A table displaying all instances of a record.
- button — A clickable button that executes a flow when clicked. Buttons must be block‑only (no one‑line syntax). Within a button block, you can only call a flow via calls flow "name" .

namel3ss enforces that pages remain declarative: no variables or control flow inside pages.

### UI Engine Actions

The engine supports deterministic actions with unique IDs:

- call_flow — Executes a backend flow.
- submit_form — Validates and saves a record from a form submission, returning structured validation errors if needed.

When you build a UI manifest, each button and form becomes an action with a unique ID derived from the page name, element type and label. For example, page.home.button.seed or page.home.form.user . The action ID remains stable across formatting and minor edits, making it safe to call from the CLI and Studio.

## Part V: Data Modelling & Persistence

Records define data schemas, constraints and engine behaviour. They look similar to database table definitions but live entirely in your program.

### Declaring a Record

Use the record keyword:

```
record "User":
 field "email" is text present unique pattern "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"
 field "name" is text present
 field "age" is int gt 0
```

- field "name" — Declares a field with a type and constraints.
- Types — text , int , float , bool , date , datetime .
- Constraints — present (required), unique , gt , lt , pattern , length (min/max), etc.

Constraints are validated at engine. For example, the email field must match a regex and be unique across all User records. Attempting to save a record with duplicate email will return a structured error.

### Saving and Finding Records

In flows, you use the save statement to insert or update records:

```
save User {
 email is input.email
 name is input.name
 age is input.age
}
```

The save operation validates data against field constraints and inserts it into an in‑memory store. If validation fails, the engine throws an error or returns structured validation errors in form submissions.

To retrieve records, use the find statement:

```
let users is find User where email is input.email
```

find returns a list of matching records. You can also specify multiple criteria joined by and or or .

At present, find operations support simple comparisons (equal, less than, greater than) and combine them with logical and / or . Future versions may expand query capabilities.

### Persistence and Uniqueness

By default, namel3ss stores records in an in‑memory store for the duration of program execution (i.e. while your CLI or Studio process runs). If you restart the process, data resets. Future versions may introduce persistent backends (e.g. SQLite) with minimal changes to the language. Meanwhile, you can rely on the deterministic state when building prototypes and demos.

Uniqueness constraints ensure that no two records share the same value in a unique field. When saving a record, if a value already exists, the engine returns a structured error with code unique . You can catch and handle this error in a flow or display it as form validation in the UI.

## Part VI: Full‑Stack UI

namel3ss generates user interfaces directly from your .ai code. Pages combine forms, tables, text and buttons into a coherent UI. The UI manifest is pure JSON and can be rendered in web clients or inspected via the CLI.

### Forms

A form bound to a record auto‑generates input fields for each record field. When a user submits a form, the engine validates each field against the record’s constraints and returns structured errors if any exist. For example:

```
page "signup":
 form is "User"
```

When submitted, the engine returns errors like:

```
{
 "ok": false,
 "errors": [
  {"field": "email", "code": "unique", "message": "Email must be unique"},
  {"field": "age", "code": "gt", "message": "Age must be greater than 0"}
 ]
}
```

### Tables

A table displays all stored records of the bound record type. When you save records via flows or forms, the table automatically refreshes. You can provide simple row previews via the UI manifest and implement sorting and filtering in future versions.

### Buttons

Buttons are blocks that call flows. They must be written in the canonical form:

```
button "Create":
 calls flow "create_user"
```

When clicked, the UI calls the call_flow action for the referenced flow. Buttons cannot contain arbitrary logic or multiple actions. Keeping buttons simple ensures that action IDs remain deterministic and the UI stays predictable.

### UI Manifest

The CLI command `n3 <file>.ai ui` prints the UI manifest as JSON. It includes pages, forms, tables, buttons, labels, descriptions, action IDs, and the type of each action. The manifest also includes table row previews and any validation messages returned by actions. You can use the manifest in custom frontends or embed it in frameworks.

## Part VII: Backend Logic (Flows)

Flows are the heart of your application logic. A flow processes input, manipulates state, saves or finds records, calls AI profiles, runs agents, loops and branches, and ultimately returns a value.

### Anatomy of a Flow

A flow is declared with:

```
flow "name":
 # statements
```

A flow has no formal parameters. Instead, it can read from the input object bound by the caller (e.g. a form submission or button). The state object contains persistent state across flows and records. Flows can also access constants and variables they declare.

The body of a flow is a sequence of statements. These may include:

- Variable declarations ( let ) and assignments ( set ).
- Control flow statements ( if , repeat up to , for each , match , try ).
- Record operations ( save , find ).
- AI calls ( ask ai ).
- Agent calls ( run agent , run agents in parallel ).
- Returning a value ( return ).

### State and Variables

Flows have access to a mutable state dictionary. The state persists between flows and across UI sessions (within a process). You can set nested attributes on the state:

```
set state.user is {
 id is 1
 name is "Alice"
}
```

Later, you can reference state.user.id in expressions. The input dictionary contains values passed to the flow by the caller. For example, a form submission populates input.values , where each key is a field name.

### AI Calls

The ask ai statement calls an AI profile and captures its reply. The canonical syntax is:

```
flow "chat":
 ask ai "assistant" with input: "Hello" as reply
 set state.reply is reply
 return reply
```

- ask ai "profile" — Specifies which AI profile (declared with ai block) to call.
- with input: <expression> — Specifies the message to send to the model.
- as <variable> — Binds the reply to a variable.

namel3ss supports only one input: per call and no additional parameters. Inside the AI block, you define the model, provider, memory settings, system prompt and tools. The engine collects the AI input, invokes the provider and returns a reply. The reply always becomes a string (or list of strings for multi‑agent results). Tools are called only if the AI output triggers a tool_call object, subject to guardrails.

### Tools

Tools allow the AI to call functions in your engine. You expose tools via an AI profile:

```
ai "assistant":
 provider is "openai"
 model is "gpt-4.1"
 tools:
  expose "echo"
# tool implementation in code (mock example)
tool "echo":
 # This is defined in Python outside the `.ai` file
```

When the AI triggers a tool call (e.g. {"name":"echo", "arguments": {...}} ), the engine executes the tool and returns its result back to the AI as a message. The tool loop includes guardrails: a maximum number of tool calls per AI call to prevent infinite loops. The default guardrail is usually 3 or 5 calls. Tools must be explicitly exposed; otherwise, AI cannot call them.

### Memory

AI profiles define three memory types:

- short‑term (size integer) — Keeps the last n messages of context (user and assistant).
- semantic (boolean) — Enables simple retrieval of semantically similar past messages from a vector store.
- profile (boolean) — Stores the AI’s own profile information (e.g. system prompts and tool schemas) to recall later.

For example:

```
ai "assistant":
 provider is "ollama"
 model is "llama3.1"
 memory:
  short_term is 10
  semantic is true
  profile is true
```

During each ask ai , the engine recalls relevant memory and prepends it to the prompt. After receiving a reply, the engine records the interaction. Memory scopes by state.user.id if present; otherwise, it defaults to a common key.

### Try/Catch and Validation

Flows may throw engine errors or receive validation errors from record operations. Use try / catch to handle them:

```
try:
 save User {
  email is input.email
  name is input.name
 }
catch error:
 return error
```

error becomes a structured object with fields like message , code and fields . Return it directly to propagate the error to the UI or handle internally.

## Part VIII: AI Profiles & Providers

AI profiles define how the system interacts with models. They specify the model, provider, system prompt, memory, tools and other behaviour.

### AI Profile Syntax

```
ai "assistant":
 provider is "openai"
 model is "gpt-4.1"
 system_prompt is "You are a helpful assistant."
 memory:
  short_term is 10
  semantic is true
  profile is true
 tools:
  expose "echo"
 auth:
  api_key is env "OPENAI_API_KEY"
 endpoint:
  base_url is "https://api.openai.com"
  timeout_seconds is 30
```

- provider — The provider name: mock (default), ollama , openai , anthropic , gemini , mistral . Each provider supports a set of models.
- model — The model name (provider‑specific).
- system_prompt — A string sent as a system prompt.
- memory — Defines memory behaviour (see above).
- tools — Lists tools exposed to this AI profile.
- auth — Specifies how to load secrets (via environment variables or secret references).
- endpoint — Overrides host and timeouts (optional).

### Providers

namel3ss includes first‑class support for major providers via standard HTTP clients. The provider registry maps names to classes that implement the AIProvider interface.

- mock — Returns fixed responses; used in tests and examples.
- ollama — Calls a locally running Ollama server (default host http://127.0.0.1:11434 ); no API keys needed.
- openai — Calls OpenAI Chat or Responses API using your API key.
- anthropic — Calls Anthropic’s Messages API (e.g. Claude models).
- gemini — Calls Google Gemini’s generateContent API.
- mistral — Calls Mistral’s Chat completions API.

Each provider requires specific environment variables for authentication:

- NAMEL3SS_OPENAI_API_KEY , NAMEL3SS_OPENAI_BASE_URL (optional)
- NAMEL3SS_ANTHROPIC_API_KEY
- NAMEL3SS_GEMINI_API_KEY
- NAMEL3SS_MISTRAL_API_KEY
- NAMEL3SS_OLLAMA_HOST , NAMEL3SS_OLLAMA_TIMEOUT_SECONDS (optional)

You can specify them in .env or export them in your shell. When missing, the engine raises a friendly error like Missing OPENAI_API_KEY (set it in .env or export it) .

### Provider Adapter Internals

Each provider implements ask() using Python’s standard urllib.request . No third‑party HTTP libraries are used. The provider constructs a request body with fields: model, system prompt, input messages, memory context and tools. It sends an HTTP request to the provider’s endpoint with proper headers (e.g. Authorization: Bearer <key> ). The response is parsed into an AIResponse object with the output string. Errors such as missing keys, invalid HTTP responses and timeouts raise Namel3ssError with consistent messages. By standardising inputs and outputs, the engine remains predictable.

### Tools and AI Integration

When a provider returns a tool_call result (OpenAI tool calling feature), the engine decodes the tool name and arguments, looks up the tool in the registry and executes it. The result is returned back to the AI profile, which may continue the conversation or finish. The engine limits the number of tool calls per AI call to avoid infinite loops.

## Part IX: Multi‑Agent Orchestration

Agents encapsulate AI profiles with an optional system prompt override. They are used to coordinate tasks across multiple AI instances. An agent is declared with:

```
agent "planner":
 ai is "assistant"
 system_prompt is "You plan tasks."
```

- ai is "profile" — Links the agent to an AI profile.
- system_prompt is "..." — Overrides or augments the profile’s system prompt.

### Running a Single Agent

You run an agent in a flow via the statement:

```
run agent "planner" with input: task as plan
```

This executes the AI call and binds the result to plan . The engine adds an AITrace entry to the trace list with fields: agent name, AI name, input, output, tool calls, memory used. The trace appears in the final program response and in Studio’s Traces panel.

### Running Agents in Parallel

You can run multiple agents concurrently using the parallel syntax:

```
run agents in parallel:
 agent "critic" with input: plan
 agent "researcher" with input: plan
as results
```

This executes each agent sequentially under the hood but wraps their traces in a single parallel_agents trace with a list of child traces. It binds the outputs to a list variable results in the same order as defined. Guardrails limit the number of parallel agents (e.g. 3) and the total agent calls per flow.

When one agent fails (e.g. due to provider error), the engine fails the entire statement and returns a clear error like Agent 'critic' failed: Provider 'openai' unreachable .

## Part X: Tooling & CLI

namel3ss provides a robust CLI and additional tools to improve developer experience.

### CLI Commands

All commands start with `n3 <file>.ai` and then add subcommands:

- check — Parse and lower the .ai file. Print OK on success or a formatted error.
- ui — Print the UI manifest as JSON.
- actions — List all available action IDs, types and details. Optional json argument prints JSON instead of plain text.
- format — Format the source code. Use format check to verify if formatting is needed.
- lint — Run the linter. Use lint check to exit non‑zero if findings exist.
- studio — Launch the visual Studio. Optional --port sets the port.
- `<action_id>` — Execute a specific UI action. Provide payload JSON if needed (e.g. for form submissions).
- new `<template>` `[project_name]` — Scaffold a new project from a template.
- help — Show usage information.

The CLI routes commands based on the second argument after the file name. It loads .env before running any command to make environment variables available.

### Formatter and Linter

The built‑in formatter ensures your code is canonical: two‑space indents, block only button declarations, single spaces around is , no extra blank lines, and canonical ask ai syntax. It can rewrite one‑line button forms into block form. The linter warns about pages using imperative statements, legacy grammar (e.g. flow is "name" ), unknown references (e.g. pages calling unknown flows), and reserved words used as identifiers.

### Studio

The Studio is a web interface powered by a lightweight Python HTTP server. When you run `n3 <file>.ai studio`, the CLI loads your code, builds the manifest, runs lint and sets up state. It serves the UI and API endpoints for summary, actions, lint findings, state, traces and editing. The Studio viewer shows the UI and can execute actions. The interactor extends this with a state panel, traces panel and error messages. The safe edit feature lets you edit titles, text and button labels. When you edit, the server applies changes to the source code, runs the formatter, re-parses, re-lowers and updates the UI, ensuring code remains valid.

### Secret Management

Secrets should never be stored directly in .ai files. Use environment variables or .env to store API keys. The CLI automatically loads .env and respects environment variables. The auth block in AI profiles defines which env keys to load. For example:

```
ai "assistant":
 provider is "openai"
 model is "gpt-4.1"
 auth:
  api_key is env "OPENAI_API_KEY"
```

If the key is missing, the engine raises an error with a clear message.

## Part XI: Examples & Demos

This section illustrates complete applications using namel3ss.

### CRUD Dashboard Example

```
record "Customer":
 field "email" is text present unique pattern "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"
 field "name" is text present
 field "age" is int gt 17

page "dashboard":
 title is "Customer Dashboard"
 text is "Manage your customers."
 form is "Customer"
 table is "Customer"
 button "Seed":
  calls flow "seed_customers"

flow "seed_customers":
 repeat up to 2:
  save Customer {
   email is "demo_" + random_int().to_string() + "@example.com"
   name is "Demo User " + random_int().to_string()
   age is 30
  }
 return "Seeded"
```

This defines a Customer record with validation, a page with a form and table, and a seed flow that inserts two demo customers. When run, the table shows these records. Submitting the form adds new customers and triggers validation errors if email is invalid or duplicate.

### AI Assistant Over Records

```
record "Note":
 field "title" is text present
 field "body" is text present

ai "assistant":
 provider is "ollama"
 model is "llama3.1"
 memory:
  short_term is 10
  semantic is true
  profile is true

page "notes":
 title is "Notes"
 form is "Note"
 table is "Note"
 button "Ask Assistant":
  calls flow "ask_assistant"

flow "ask_assistant":
 let content is "Summarize the latest note."
 if size(find Note) is greater than 0:
  set content is "Summarize this note: " + (find Note)[-1].body
 ask ai "assistant" with input: content as reply
 set state.reply is reply
 return reply
```

This app lets you create notes and then ask an AI to summarize the most recent note. The flow checks if there are notes and adjusts the prompt. It stores the reply in state.reply and returns it. The Studio trace shows the AI input and output. You can switch providers by changing the provider and setting the corresponding API key in .env .

### Multi‑Agent Workflow Example

```
ai "base":
 provider is "ollama"
 model is "llama3.1"
 memory:
  short_term is 5
  semantic is true
  profile is true

agent "planner":
 ai is "base"
 system_prompt is "You are a project planner."

agent "critic":
 ai is "base"
 system_prompt is "You are a critic that finds flaws."

agent "researcher":
 ai is "base"
 system_prompt is "You are a researcher who looks for supporting facts."

flow "run_workflow":
 let task is "Write a launch plan for namel3ss"
 run agent "planner" with input: task as plan
 run agents in parallel:
  agent "critic" with input: plan
  agent "researcher" with input: plan
 as feedback
 ask ai "base" with input: "Combine the plan and feedback into a final summary" as summary
 set state.plan is plan
 set state.feedback is feedback
 set state.summary is summary
 return summary

page "workflow":
 title is "Launch Workflow"
 button "Run":
  calls flow "run_workflow"
 text is "Plan, critique and research automatically."
 text is "Summary: " + state.summary
```

This example shows how to orchestrate multiple agents. The planner creates a plan; the critic and researcher review it in parallel; then a final AI compiles everything into a summary. The UI displays the summary. Traces expose the plan, feedback and summary, illustrating how multi‑agent conversations unfold.

## Part XII: Glossary

A quick reference to all the key terms in namel3ss:

- app — The entire program or .ai file containing flows, records, pages, AI profiles, tools and agents.
- flow — A named block of backend logic. Flows process input, manage state, call AI, run agents and return a value.
- record — A data model with fields and constraints. Records validate and persist data.
- field — A property within a record; has a type and constraints.
- constraint — A rule like present , unique , gt , lt , pattern , length applied to fields.
- page — A user interface block containing titles, text, forms, tables and buttons. Pages are declarative.
- form — A UI element bound to a record. Generates inputs for each field and validates on submission.
- table — A UI element showing stored records with live refresh.
- button — A clickable UI element that calls a flow. Defined with a block and calls flow property.
- action — A deterministic UI action; either call_flow or submit_form . Identified by a stable action ID.
- AI profile — A block defining how to call an LLM. Specifies provider, model, system prompt, memory and tools.
- provider — An abstraction over an LLM API (e.g. ollama , openai , anthropic , gemini , mistral , mock ).
- memory — Mechanisms for storing conversation context: short_term , semantic , profile .
- tool — A function external to the AI that can be invoked by the AI via tool calling. Exposed via AI profiles.
- agent — A wrapper around an AI profile with an optional system prompt override; used for multi‑agent orchestration.
- ask ai — A statement in flows that calls an AI profile with an input and binds the reply.
- run agent — Executes an agent sequentially in a flow.
- run agents in parallel — Executes multiple agents concurrently (internally sequential) and returns a list of results.
- state — A dictionary holding global state across flows; persists for the lifetime of the program process.
- input — A dictionary containing values passed to a flow (e.g. form values).
- variable — A local binding created with let or mutated with set . Can be constant.
- expression — A value or operation used on the right side of is . Includes literals, variables, state paths, arithmetic, comparisons and boolean logic.
- control flow — Constructs like if , repeat up to , for each , match , try , return used to control flow of a program.
- UI manifest — A JSON description of pages, elements, actions and previews. Generated by the compiler.
- traces — A list of engine events, particularly AI calls and agent calls, including inputs, outputs, tools and memory used.
- formatter — A tool that rewrites code into canonical form.
- linter — A tool that analyses code for best practices and potential issues.
- Studio — A web interface for viewing pages, executing actions, inspecting state and traces, and making safe edits.
- template — A predefined project scaffold (starter, demo) used by n3 new.
- test — Python or .ai tests that verify correctness. Tests mirror the src directory.
- error — A structured error with message, code and context. Errors come from validation, engine or parsing.
- guardrail — A engine limit (e.g. maximum number of agent calls) to prevent misuse.
- wow moment — A feature that demonstrates namel3ss’s value: record → UI, AI calls with trace, multi‑agent orchestration, safe edits, provider integration.

## Part XIII: Appendices

### Appendix A: Error Codes

namel3ss defines several error codes:

| Category | Code | Description |
| --- | --- | --- |
| Parser | parser_error | Raised when .ai source contains invalid syntax or unknown tokens. |
| Lexer | lexer_error | Raised when unexpected characters are encountered. |
| Validation | validation_error | Raised when record constraints fail. Fields include field , code and message . |
| Engine | engine_error | Raised for logic errors such as undefined variables or invalid operations. |
| AI | ai_error | Raised when AI calls fail (missing key, unreachable provider, timeout, invalid response). |
| Tool | tool_error | Raised when a tool call fails. |

The error message shows the line and column, the offending line, and a caret (^) pointing to the error column. Use the CLI and Studio to see formatted errors.

### Appendix B: Config File Format

If you prefer not to use .env , you can create ~/.namel3ss/config.json :

```
{
"openai": {
"api_key": "sk-...",
"base_url": "https://api.openai.com"
},
"anthropic": {
"api_key": "sk-..."
},
"gemini": {
"api_key": "sk-..."
},
"mistral": {
"api_key": "sk-..."
},
"ollama": {
"host": "http://127.0.0.1:11434",
"timeout_seconds": 30
}
}
```

The engine merges config from this file with environment variables. Use environment variables to override config values.

### Appendix C: Studio API Endpoints

Studio runs a local HTTP server with these endpoints:

- GET /api/summary — Returns counts of records, flows, pages, AI profiles, agents and tools.
- GET /api/ui — Returns the UI manifest with pages and actions.
- GET /api/actions — Returns a list of action definitions.
- GET /api/lint — Returns linter findings as JSON.
- POST /api/action — Executes an action; body includes id and payload .
- POST /api/edit — Applies a safe edit; body includes operation, target and value.
- POST /api/reset — Resets state and store.

These endpoints make Studio interactive and enable integration with other frontends.

## Afterword

namel3ss  0.1.0a7 is a revolutionary step towards building AI‑native applications in plain English. By integrating full‑stack development, AI orchestration, deterministic engine semantics and robust tooling, namel3ss eliminates friction and reduces cognitive load for developers. In this book you learned the grammar, features, tooling and best practices of namel3ss. You should now feel comfortable creating records, flows, pages, AI profiles and agents, exploring the UI and Studio, running and testing applications, and scaffolding new projects with templates.

We are just at the beginning of this journey. Future versions of namel3ss will introduce persistent storage backends, user authentication, additional providers and more advanced agent capabilities — but the foundation of structured English for deterministic full‑stack AI development remains. Join the community, build amazing apps, and help shape the future of software development.

Thank you for reading.
