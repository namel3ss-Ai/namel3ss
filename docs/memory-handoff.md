# Memory Handoff

Agent lanes store private memory for one agent.
Agent lanes are not shared by default.

## Agent lane
- Each agent has its own lane
- The lane is private to that agent
- The agent id is stored in meta

## Handoff packet
A handoff packet moves selected memory from one agent to another.
It copies items into the target agent lane.
The original items stay in place.

## What goes into a packet
- Latest decisions
- Pending proposals
- Open conflicts
- Active rules
- Recent impact warnings

## Status
- pending
- applied
- rejected

## How to create and apply
- Open Studio
- Open Handoff
- Pick a from agent and a to agent
- Click Create handoff
- Review the packet preview
- Click Apply or Reject

## Briefing
The packet includes short briefing lines.
The agent briefing shows what to focus on.

## Trust and rules
Trust rules control who can create, apply, and reject.
Rules can also block handoff actions.

## Trace events
- memory_handoff_created
- memory_handoff_applied
- memory_handoff_rejected
- memory_agent_briefing

## Determinism and privacy
Handoff selection is deterministic.
Agent lanes stay private without a handoff.
