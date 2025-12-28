# Memory Trust

Trust levels control team memory actions.
Trust is simple and deterministic.

## Trust levels
- viewer
- contributor
- approver
- owner

## What each level can do
Viewer can read team memory.
Contributor can propose team memory.
Approver can approve and reject proposals.
Owner can override when override is enabled.

## Approval rules
Proposals need one or two approvals.
The required count is part of the trust rules.
The same person cannot approve twice.

## Why actions are blocked
Blocked actions emit a trust check event.
The event says the required level and the actor level.
It also says why the action was blocked.

## Studio
Open Studio and select the Team lane.
The trust panel shows your level and the rules.
Blocked actions show a simple explanation.

## Trace events
- memory_trust_check
- memory_approval_recorded
- memory_trust_rules

## Determinism
Trust decisions are rule based and trace backed.
The same inputs always produce the same decisions.
