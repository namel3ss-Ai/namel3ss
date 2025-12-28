# Memory Agreement

Team memory changes need agreement.
A proposal is created first.
Pending proposals do not affect recall or impact.
Approving creates active team memory.
Rejecting removes the proposal.

## Agreement states
- pending
- approved
- rejected

## How to approve or reject
- Open Studio
- Open Traces
- Select lane Team
- Review proposals
- Click Approve or Reject

## Trace events
- memory_proposed
- memory_approved
- memory_rejected
- memory_agreement_summary

## Determinism
Proposals and decisions are deterministic and trace backed.

## Trust
Team proposals follow trust rules.
Propose needs contributor or higher.
Approve needs approver or higher.
Reject needs approver or higher.
Approvals required can be one or two.
Owner override can approve immediately when enabled.
See docs/memory-trust.md for full trust rules.

## Trust traces
- memory_trust_check
- memory_approval_recorded
- memory_trust_rules
