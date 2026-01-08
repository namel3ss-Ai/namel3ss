# Invariants v1

## Contract status (public)
- Status: frozen
- Applies to: invariants catalog
- Freeze semantics: public contract; changes must be additive and explicitly documented

This catalog lists the invariants frozen for v1. Each entry includes the
primary enforcement location and pass/fail fixtures.

| id | description | enforcement | pass fixture | fail fixture |
| --- | --- | --- | --- | --- |
| INV-001-old-tool-syntax-forbidden | Old tool syntax is forbidden and rejected by the parser. | parser | spec/programs/tools/tool_call_binding/app.ai | tests/parser/test_tool_old_syntax_rejected.py |
| INV-002-tool-call-traced | Tool calls always emit a tool_call trace event. | runtime | spec/programs/tools/tool_call_binding/app.ai | resources/invariants/tool_trace_missing.md |
| INV-003-tool-resolution-precedence | Tool resolution precedence is deterministic: builtin_pack > installed_pack > binding. | runtime | spec/programs/packs/builtin_pack/app.ai | spec/failures/packs/collision/app.ai |
| INV-004-collisions-hard-error | Tool collisions never shadow; they fail with a hard error. | runtime | spec/programs/packs/installed_pack/app.ai | spec/failures/packs/collision/app.ai |
| INV-005-unverified-pack-blocked | Unverified packs cannot execute tools. | runtime | spec/programs/packs/installed_pack/app.ai | spec/failures/packs/unverified_pack/app.ai |
| INV-006-enabled-unverified-pack-blocked | Enabled but unverified packs are still blocked. | runtime | spec/programs/packs/installed_pack/app.ai | spec/failures/packs/enabled_unverified_pack/app.ai |
| INV-007-runner-no-silent-fallback | Runner selection has no silent fallback; unknown runners hard error. | runtime | spec/programs/runners/local/app.ai | spec/failures/runners/unknown_runner/app.ai |
| INV-008-tool-protocol-version-present | Tool protocol version is present in tool traces and runner requests. | runtime | spec/programs/runners/local/app.ai | resources/invariants/tool_protocol_missing.md |
| INV-009-secrets-redacted | Secrets are redacted in proofs and observe logs. | governance | spec/programs/governance/proof/app.ai | resources/invariants/secrets_redaction_fail.md |
| INV-010-intent-only-ai | .ai remains intent-only; no module:function or JSON schema blobs. | lint | spec/programs/language_core/let_set_if_repeat.ai | resources/invariants/intent_only_fail.ai |
| INV-011-no-network-blocks | no_network blocks any network operation. | runtime | spec/programs/capabilities/builtin_pack_network_block.ai | spec/failures/capabilities/forbidden_network.ai |
| INV-012-no-filesystem-write-blocks | no_filesystem_write blocks any filesystem write. | runtime | spec/programs/capabilities/builtin_pack_fs_write_block.ai | spec/failures/capabilities/forbidden_fs_write.ai |
| INV-013-policy-downgrades-enforced | Policy downgrades are enforced for effective guarantees. | runtime | tests/runtime/test_capability_policy.py | resources/invariants/policy_downgrade_fail.md |
| INV-014-sandbox-blocks-user-writes | Sandboxed user tools cannot write to the filesystem. | runtime | spec/programs/capabilities/user_tool_sandbox_block/app.ai | resources/invariants/sandbox_user_write_fail.md |
| INV-015-service-handshake-blocks-unsafe | Service runner handshakes block unenforced guarantees. | runtime | spec/programs/capabilities/service_handshake_block/app.ai | resources/invariants/service_handshake_fail.md |
