# Memory Rules

Rules are short sentences.
A rule is stored as a memory item.
Rules live in the team lane or system lane.
Rules are enforced during proposals and approvals.
Rule decisions emit trace events.

## Rule sentences
Only approvers can approve team proposals.
Only owners can change system memory.
Two approvals are needed for team changes.
Team memory cannot store personal preferences.
Only contributors can create handoff packets.
Only approvers can apply handoff packets.
Only owners can reject handoff packets.

## How rules are approved
Open Studio.
Go to Rules.
Propose a rule sentence.
Approve the proposal.
The latest approved rule is active.

## Enforcement and traces
Rule checks emit memory_rule_applied.
Rule snapshots emit memory_rules_snapshot.
Rule changes emit memory_rule_changed.
Traces include the rule text and a clear decision.
Rules can also control handoff actions.

## Studio view
Rules shows active and pending rules.
Use Approve and Reject for proposals.
Open Traces to see rule decisions.
Use Explain to see why a rule applied.
