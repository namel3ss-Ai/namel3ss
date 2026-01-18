# Pack Intent
## What this pack does
Provides outbound HTTP JSON fetches with deterministic response shaping.

## Tools provided (English)
- "http get json"

## Inputs/outputs summary
Accepts a URL and optional headers, returning status, headers, and body.

## Capabilities & risk
Uses outbound network access only.

## Failure modes
Returns errors for invalid URLs or malformed payloads.

## Runner requirements
Runs locally with network access.
