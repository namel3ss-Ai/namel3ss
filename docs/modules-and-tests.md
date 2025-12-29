# Modules and Tests

This page covers module files and the built in test runner.

## Module files

Modules are plain ai files.
A module can define functions, records, tools, and pages.
Modules do not define flows, ai profiles, agents, or app theme.

Example paths
modules/inventory.ai
modules/pricing.ai

## Using modules

Use module with a path and an alias.

use module "modules/inventory.ai" as inv

Imported items are used by name in your app.
Aliases are for trace and provenance.

Rules
- Paths are relative to the project root.
- Conflicts are errors unless allow override is declared.
- Later use module statements are merged later.

## Capsules and packages

Capsules are the package format used under packages.
Capsules still use the legacy use syntax.

## Tests

Test files live under tests and end with _test.ai.
Run tests from the project root.
n3 test
n3 test --json
