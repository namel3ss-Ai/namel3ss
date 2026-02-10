# Security Policy

## Supported versions

| Version range | Status | Security support |
| --- | --- | --- |
| 1.0.x | GA | full support |
| 0.x | pre-GA | best effort |

## Reporting a vulnerability

Report vulnerabilities privately to `info@namel3ss.com` with subject `[SECURITY]`.

Include:

- summary of the issue
- impact and affected modules
- reproduction steps
- version and environment details
- proof of concept (if available)

Do not open public issues for security vulnerabilities.

## Response timeline

- Initial response: within 2 business days
- Triage decision: within 7 calendar days
- Status updates: at least weekly until resolution

## Disclosure policy

Namel3ss follows coordinated disclosure:

1. Vulnerability is confirmed privately.
2. Fix is prepared and validated.
3. Patch is released with security notes.
4. Public disclosure occurs after patch availability.

## Security boundaries

- Plugin execution is sandboxed with explicit API allowlists.
- Runtime and compiler fail closed on policy violations.
- i18n/theme/plugin asset loaders reject invalid payloads with explicit errors.
- Release artifacts are reproducible and checksummed.

## Security hardening expectations

- No arbitrary code execution from manifests or plugins.
- No hidden write paths outside allowed runtime locations.
- Deterministic error behavior for malformed or hostile inputs.

## Contact

- Email: `info@namel3ss.com`
- Security updates are announced in release notes and changelog entries.
