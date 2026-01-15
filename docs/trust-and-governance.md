# Trust & Governance

namel3ss treats production as a provable, explainable, governable state. This phase adds engine proofs, verification gates, secrets-as-capabilities, observability exports, and explainability.

**Engine**: the system that runs a namel3ss app and enforces its rules.

---

## Engine proof
Create an immutable snapshot of what the engine will run.
```bash
n3 proof --json
```
Proofs are stored as managed runtime artifacts. Use `n3 proof` to regenerate them and
`n3 clean` to remove artifacts.

---

## Verify (governance gate)
Run CI-friendly checks before shipping.
```bash
n3 verify --prod --json
```
Verify enforces secrets redaction, access control safety, package integrity, pack capability review, engine readiness, and determinism.
It also checks tool guarantee coverage (runners must be able to enforce declared guarantees).
In production mode it additionally requires:
- local tools use sandbox (unless pure),
- service runners require capability handshake,
- container runners declare verified enforcement.

Unsafe overrides are blocked by default:
```bash
n3 verify --prod --allow-unsafe --json
```

## Pack review (local)
Packs are reviewed before bundling and signing.
```bash
n3 packs review ./my_pack --json
```
Review surfaces tool names, runners, capabilities, collision risks, and intent coverage.

Trust policy can gate pack installs/enables:
```toml
allow_unverified_installs = false
max_risk = "medium"
allowed_capabilities = { network = "outbound", filesystem = "read", subprocess = "none" }
```

Policy restrictions are enforced at runtime; denied operations emit `capability_check` traces.

---

## Secrets (capabilities)
Secrets are referenced by name and injected at call time. Values are never printed.
```bash
n3 secrets status --json
n3 secrets audit --json
```

---

## Observe (engine-native)
Get a stream of engine events without manual wiring.
```bash
n3 observe --since 10m --json
```
Events include flows, actions, AI calls, audits, and engine errors (redacted).

---

## Explain (current state)
Explain the current proven state for human and CI consumption.
```bash
n3 explain --json
```

---

## Notes
- Proofs and verify output are deterministic; runtime artifacts are canonicalized without timestamps or call ids.
- Secrets are never stored in proofs, logs, or trace exports.
- `.namel3ss` is read via the CLI (`n3 status`, `n3 explain`, `n3 clean`) and remains safe to delete when needed.
- Edge target remains a stub in this alpha; verify and explain will flag limitations clearly.
