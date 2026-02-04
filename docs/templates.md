# Templates

Templates are curated starter apps. Each template is deterministic and includes `expected_ui.json`.

There are two template systems:
- Scaffold templates live in `src/namel3ss/templates/` and are created with `n3 new <name>`.
- Shortcut templates live in `templates/` and are opened with `n3 kb`, `n3 ops`, or `n3 aid`.

Note: `.namel3ss/` is local runtime output. Do not commit it, and teaching assets must not rely on it.

## Scaffold templates

## Operations Dashboard
- Demonstrates: grouped layout, table configuration, compose blocks, and story tone usage.
- Location: `src/namel3ss/templates/operations_dashboard/`
- Run:
```bash
n3 new operations_dashboard ops_app
cd ops_app
n3 run
n3 app.ai ui
n3 app.ai studio
```

## Onboarding
- Demonstrates: list variants, compose blocks, and calm checklist copy.
- Location: `src/namel3ss/templates/onboarding/`
- Run:
```bash
n3 new onboarding onboarding_app
cd onboarding_app
n3 run
n3 app.ai ui
n3 app.ai studio
```

## Composition
- Demonstrates: contracts, pipelines, orchestration, and composition boundaries.
- Location: `src/namel3ss/templates/composition/`
- Run:
```bash
n3 new composition composition_app
cd composition_app
n3 run
n3 app.ai ui
n3 app.ai studio
```

## Support Inbox
- Demonstrates: queue tables, compose metrics, and action discipline.
- Location: `src/namel3ss/templates/support_inbox/`
- Run:
```bash
n3 new support_inbox support_app
cd support_app
n3 run
n3 app.ai ui
n3 app.ai studio
```

## Shortcut templates

### Knowledge
- Location: `templates/knowledge/`
- Run:
```bash
n3 kb
```

### Operations
- Location: `templates/operations/`
- Run:
```bash
n3 ops
```

### Support
- Location: `templates/support/`
- Run:
```bash
n3 aid
```
