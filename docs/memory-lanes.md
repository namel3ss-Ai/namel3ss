# Memory Lanes

Memory lanes separate what is mine and what is ours.
Lanes are my, team, agent, and system.

## Lanes
- My lane stores personal memory for the current user
- Agent lane stores private memory for one agent
- Team lane stores shared project memory
- System lane stores system rules and is read only

## How items enter team lane
- Items move to team lane only by promotion
- Promotions are policy driven and trace backed
- Decisions, rules, and tool outcomes can be promoted by default

## Visibility and change
- visible_to shows who can read the item
- can_change shows if normal writes can change the item

## Agent handoff
Agent lane items are private by default.
Handoff copies selected items to another agent lane.
Handoff does not change the original items.

## Team change summary
A team change summary is emitted for phase diffs in the team lane.
It reports what changed between two phases in team memory.
The trace event type is memory_team_summary.

## Team agreements
Team lane writes create proposals first.
Pending proposals are not recalled or used for impact.
Approvals create active team memory.
Rejections remove the proposal.

## Team trust
Team agreement actions follow trust rules.
Viewer can read only.
Contributor can propose.
Approver can approve and reject.
Owner can override when enabled.

## Studio
- Open Studio
- Open Traces
- Use the lane selector
- Team lane shows the latest team change summary when available
- Team lane shows pending proposals and approval actions
