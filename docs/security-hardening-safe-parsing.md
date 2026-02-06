# Security Hardening and Safe Parsing

This phase removes risky execution paths and adds a repeatable hardening gate.

## What was removed

- Dynamic runtime evaluation via `eval` and `exec` is blocked by policy and scan.
- Shell-style command execution via `os.system` is blocked by policy and scan.
- `subprocess(..., shell=True)` is blocked by policy and scan.
- String command arguments to subprocess are blocked by policy and scan.

## Safe parsing path

- The runtime uses parser and IR nodes for expression evaluation.
- Guarded literal-only evaluation now goes through `runtime/safe_expression.py`.
- Allowed expression subset is explicit:
  - literal values
  - unary `+` and `-` on numeric literals
- Unsupported expressions fail with deterministic errors.

## Security scan contract

Run:

```bash
python tools/security_hardening_scan.py
```

Optional JSON output:

```bash
python tools/security_hardening_scan.py --json .namel3ss/ci_artifacts/security_scan.json
```

The report is deterministic and includes:

- `status` (`pass` or `fail`)
- `issue_count`
- ordered `issues` with `path`, `line`, `issue_type`, `message`

Issue types include:

- `dynamic_eval`
- `dynamic_exec`
- `os_system_call`
- `subprocess_shell_true`
- `subprocess_string_command`
- `secret_pattern`

## Secret scanning

The scanner checks for high-confidence secret signatures, including:

- OpenAI keys
- GitHub personal access tokens
- AWS access key ids
- Google API keys
- Private key headers

## Development and CI integration

- Local verification now runs the security scan before compile and tests.
- CI release-gate now runs the same security scan and stores the JSON artifact.

## Safe coding rules

- Never execute source text as code.
- Never pass shell commands through `shell=True`.
- Always use argv lists for subprocess calls.
- Keep command construction explicit and typed.
- Keep secret values out of source files, docs, and logs.
