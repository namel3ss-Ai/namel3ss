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
Contributor can create handoff packets.
Approver can approve and reject proposals.
Approver can apply handoff packets.
Owner can override when override is enabled.
Owner can reject any handoff.

## Approval rules
Proposals need one or two approvals.
The required count is part of the trust rules.
The same person cannot approve twice.

## Packs
Trust defaults can come from memory packs.
Local overrides can change the defaults.
The source is tracked and traced.

## Why actions are blocked
Blocked actions emit a trust check event.
The event says the required level and the actor level.
It also says why the action was blocked.

## Rules and trust
Rules can require higher levels.
Rule checks emit memory_rule_applied.

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
