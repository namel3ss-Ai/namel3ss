# Capability Packs Contract

Packs are capability bundles with contracts. They are not arbitrary libraries or imports.

## Definition
- Packs expose named capabilities (tools) with declared inputs, outputs, and capability boundaries.
- Packs are installed and invoked by name, not imported as modules.
- Example commands (conceptual): `n3 pack add postgres`, `n3 pack add stripe`, `n3 pack add whatsapp`.

## Principles
- **Signed**: packs carry signer metadata and verification before use.
- **Permissioned**: capabilities declare required permissions (network, filesystem, secrets, subprocess) and enforce them on every call.
- **Deterministic effect boundaries**: tool calls are traced and capability checks are recorded; runtime behavior stays deterministic outside explicit IO.

## Boundaries
- Packs replace ad-hoc dependency installs; capability declarations plus signing/verification gate execution.
- Studio and CLI read the same manifest, capabilities, and traces; no pack can alter app semantics outside declared tools.
- This contract is documentation-only; registry, installer, and runtime behavior are unchanged.

## Related docs
- `docs/tool-packs.md` for current pack flows and commands.
- `docs/capabilities.md` for capability enforcement details.
- `docs/trust-and-governance.md` for trust and signature coverage.
