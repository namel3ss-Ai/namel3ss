# Pack Intent
## What this pack does
Stores and retrieves JSON records within the pack runtime directory.

## Tools provided (English)
- "storage write json"
- "storage read json"

## Inputs/outputs summary
Write accepts a relative path and JSON payload. Read returns stored JSON.

## Capabilities & risk
Uses filesystem read/write scoped to the pack runtime root.

## Failure modes
Returns errors for invalid payloads or missing files.

## Runner requirements
Runs locally with filesystem access to the pack runtime directory.
