# Modules

Modules are plain ai files you can reuse.
A module can define functions, records, tools, and pages.
Modules do not define flows, ai profiles, agents, or app theme.
Modules do not run by themselves.

## Use module

Use a module with a path from the project root.

use module "modules/common.ai" as common

## Only block

Use only to limit what is imported.

use module "modules/common.ai" as common
only:
  functions
  records

## Allow override

Use allow override to permit a module to replace existing names.

use module "modules/common.ai" as common
allow override:
  functions

## Conflict rules

Conflicts are errors unless allow override is declared.
Later use module statements are merged later.

## Studio

Studio shows modules loaded and merge order.
Trace events include module_loaded, module_merged, and module_overrides.

## Capability id
runtime.modules
