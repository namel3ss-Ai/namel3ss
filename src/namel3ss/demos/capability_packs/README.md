# Capability Packs Demo

This demo uses a built-in pack tool alongside a background job to persist data.
Run the flow and open Studio to view Logs, Tracing, and Metrics.

- Pack: `builtin.text`
- Capability: `jobs`

## Registry walkthrough
Use the registry to discover and inspect packs before installation.

```bash
n3 registry search "greeting"
n3 registry info example.greeting
n3 pack add example.greeting@0.1.0
```

If a pack is unsigned or untrusted, installs are blocked by default:
```text
Pack "example.greeting" is blocked by policy.
Why: unverified packs are blocked by policy.
Fix: Update trust policy or choose a different pack.
Try: n3 pack add example.greeting
```

Open Studio, select the Registry tab, and review intent text, capabilities, risk,
and trust status for each available pack.
