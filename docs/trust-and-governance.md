# Trust & Governance

namel3ss treats production as a provable, explainable, governable state. This phase adds engine proofs, verification gates, secrets-as-capabilities, observability exports, and explainability.

**Engine**: the system that runs a namel3ss app and enforces its rules.

---

## Engine proof
Create an immutable snapshot of what the engine will run.
```bash
n3 proof --json
```
Proofs are stored in `.namel3ss/proofs/<proof_id>.json`, and the active pointer lives at `.namel3ss/active_proof.json`.

---

## Verify (governance gate)
Run CI-friendly checks before shipping.
```bash
n3 verify --prod --json
```
Verify enforces secrets redaction, access control safety, package integrity, engine readiness, and determinism.

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
- Proofs and verify output are deterministic (timestamps are labeled).
- Secrets are never stored in proofs, logs, or trace exports.
- Edge target remains a stub in this alpha; verify and explain will flag limitations clearly.
