# Templates

Templates are canonical, deterministic starting points for production systems. They are not demos.

## Purpose
- Provide stable, inspectable starting points for common system shapes.
- Preserve determinism, explain visibility, and repo cleanliness.

## Structure
- templates/<name>/
- templates/<name>/README.md
- templates/<name>/app.ai
- templates/index.md

## Contracts
- Templates are deterministic and explainable by default.
- Templates do not write runtime artifacts into the repo.
- Template names are stable nouns.

## Stability
- Template contracts are frozen by docs/contract-freeze.md.
- Breaking changes require explicit migration tooling and opt-in.
