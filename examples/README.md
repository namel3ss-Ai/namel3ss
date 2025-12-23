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
