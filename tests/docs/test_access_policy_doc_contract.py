from pathlib import Path


def test_access_policy_doc_contract() -> None:
    text = Path("docs/identity-and-persistence.md").read_text(encoding="utf-8")
    required = [
        "Mutation access policy",
        "mutation.action",
        "mutation.record",
        "Audit-required mode",
        "N3_AUDIT_REQUIRED",
        "requires",
    ]
    for item in required:
        assert item in text, f"Missing '{item}' in docs/identity-and-persistence.md"


def test_access_policy_trace_contract() -> None:
    text = Path("docs/trace-schema.md").read_text(encoding="utf-8")
    required = [
        "mutation_allowed",
        "mutation_blocked",
        "reason_code",
        "fix_hint",
        "policy_missing",
        "audit_required",
    ]
    for item in required:
        assert item in text, f"Missing '{item}' in docs/trace-schema.md"
