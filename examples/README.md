# Examples

## demo_product_dashboard.ai
A product-style dashboard with sections, cards, and a table of orders. Buttons seed and clear demo data.

Run:
- `n3 examples/demo_product_dashboard.ai studio`
- `n3 examples/demo_product_dashboard.ai ui`
- `n3 examples/demo_product_dashboard.ai actions`

What to click:
- In Studio, click "Seed data" then "Refresh" to see rows populate.
- Inspect the table and cards; try moving elements in the builder.
- View State and Traces after actions.

## demo_onboarding_flow.ai
A multi-step onboarding form with validation and a review card that reflects saved state.

Run:
- `n3 examples/demo_onboarding_flow.ai studio`
- `n3 examples/demo_onboarding_flow.ai ui`
- `n3 examples/demo_onboarding_flow.ai actions`

What to click:
- Fill the form (email, name, bio) and submit; fix validation errors if shown.
- See the summary card update with the saved name.
- Use Reset to clear the state and try again.

## demo_order_totals.ai
Order totals with arithmetic + if/else logic (10% discount at 100+).

Run:
- `n3 examples/demo_order_totals.ai studio`
- `n3 examples/demo_order_totals.ai ui`
- `n3 examples/demo_order_totals.ai actions`

What to click:
- Submit an order with price + quantity.
- Click "Compute total" and inspect State for the computed total.

## execution_how
A tiny flow that shows explainable execution (if/else, repeat, match).

Run:
- `cd examples/execution_how && n3 run app.ai`
- `cd examples/execution_how && n3 how`

What to look for:
- Branch taken and skipped lines.
- Repeat body skipped when count is 0.
- Match case taken and otherwise skipped.

## tools_with
A minimal tool call with explainable tool output.

Run:
- `cd examples/tools_with && n3 run app.ai`
- `cd examples/tools_with && n3 with`

What to look for:
- Tool intent and permission lines.
- Blocked tool reasons if you disable capability access.

## flow_what
A small flow showing run outcome summaries.

Run:
- `cd examples/flow_what && n3 run app.ai`
- `cd examples/flow_what && n3 with`
- `cd examples/flow_what && n3 what`

What to look for:
- Store/state/memory outcome lines.
- What did not happen bullets when persistence is skipped or fails.

## ui_see
A small ui manifest explanation demo.

Run:
- `cd examples/ui_see && n3 check`
- `cd examples/ui_see && n3 ui`
- `cd examples/ui_see && n3 see`

What to look for:
- Page list and element summaries.
- Action availability with requires details.

## errors_fix
A minimal error example for `n3 fix`.

Run:
- `cd examples/errors_fix && n3 run app.ai`
- `cd examples/errors_fix && n3 fix`

What to look for:
- Error kind and flow name.
- Recovery option to provide identity.

## b2_fix
A minimal runtime error pack demo.

Run:
- `cd examples/b2_fix && n3 app.ai flow "fail"`
- `cd examples/b2_fix && n3 fix`

What to look for:
- Deterministic error id and summary.
- Error artifacts under `.namel3ss/errors/`.

## b3_what
A minimal run outcome pack demo.

Run:
- `cd examples/b3_what && n3 run app.ai`
- `cd examples/b3_what && n3 what`

What to look for:
- Outcome status and store/state/memory flags.
- Artifacts under `.namel3ss/outcome/`.

## b4_when
A minimal spec check demo.

Run:
- `cd examples/b4_when`
- `n3 when app.ai`
- `n3 run app.ai`

What to look for:
- Declared spec and supported versions.
- Artifacts under `.namel3ss/spec/`.

## b5_with
A minimal tool gate + proof pack demo.

Run:
- `cd examples/b5_with`
- `n3 run app.ai flow "demo"`
- `n3 with`

What to look for:
- Allowed vs blocked tool entries.
- Artifacts under `.namel3ss/tools/`.

## b1_exists
A minimal contract summary demo.

Run:
- `cd examples/b1_exists && n3 exists app.ai`
- `cd examples/b1_exists && n3 app.ai flow "add_note"`

What to look for:
- Deterministic program summary.
- Features used and required capabilities.

## demo_ai_assistant_ui.ai
A lightweight AI assistant UI using the mock provider by default, with graceful messaging when real keys are missing.

Run:
- `n3 examples/demo_ai_assistant_ui.ai studio`
- `n3 examples/demo_ai_assistant_ui.ai ui`
- `n3 examples/demo_ai_assistant_ui.ai actions`

What to click:
- Enter a message and Send; if no API key, see the error message in the Status card.
- View the Messages table to see conversation entries.
- Inspect Traces after sending to observe the AI call.

## modular_inventory
Capsules + module imports + tests in a multi-file project.

Run:
- `n3 examples/modular_inventory/app.ai ui`
- `n3 examples/modular_inventory/app.ai graph`
- `n3 examples/modular_inventory/app.ai exports`
- `cd examples/modular_inventory && n3 test`

## demo_packages
Local module + external package layout with `packages/` and lockfile.

Run:
- `n3 examples/demo_packages/app.ai ui`
- `cd examples/demo_packages && n3 pkg tree`
- `cd examples/demo_packages && n3 pkg why shared`
