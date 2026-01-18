# Pack Intent
## What this pack does
Defines a deterministic Stripe API contract for apps.

## Tools provided (English)
- "stripe request"

## Inputs/outputs summary
Accepts a request payload and returns a stubbed response.

## Capabilities & risk
Declares outbound network access and a Stripe API key secret.

## Failure modes
Returns a stub error when no stub response is provided.

## Runner requirements
Runs locally; network calls are stubbed in tests.
