# Demo AI Assistant over Records

## What it shows
- Records as context using Note
- Deterministic AI with the mock provider
- Seed and ask flows to drive traces
- Memory tour with preference, decision, fact, promotion, conflict, denial, phases, diff, lanes, and agreements
- Memory budgets, compaction, and recall cache events
- Memory persistence and wake up report
- Agent lanes and handoff board
- UI with cards, form, table, and assistant action

## Try it in 60 seconds
```bash
n3 examples/demo_ai_assistant_over_records.ai check
n3 examples/demo_ai_assistant_over_records.ai ui
n3 examples/demo_ai_assistant_over_records.ai studio
```

## Key concepts
- Record validation with present and length rules
- Deterministic AI with stable replies
- Flows for seed notes and ask assistant
- UI structure with sections, cards, form, table, and assistant button
- Agent lane privacy with handoff

## Explore in Studio
- Seed the example note, then add your own notes via the form
- Click Ask assistant to see traces for the AI call
- Click Memory tour to generate memory writes, promotions, conflicts, denials, phase starts, deletions, phase diffs, and lane events
- Click Budget demo to generate memory budget and compaction events
- Click Cache demo to generate cache miss and cache hit events
- Stop Studio and run it again in the same folder
- In Traces, look for memory_wake_up_report lines
- If restore fails, look for memory_restore_failed
- In Traces, switch to Plain view and expand memory events
- In Traces, open the Memory budget section for budget lines
- Use the memory filters to show budget, compaction, and cache events
- Use the lane selector to view My, Team, and System memory
- Find memory_team_summary after the team lane phase diff
- In Team lane, review proposals and approve or reject
- Open Rules to see active and pending rules
- Propose a rule sentence and approve it
- Use the Trust buttons to run trust flows
- In Team lane, check the trust panel and blocked action notices
- Click Agent A seed to create agent memory
- Open Handoff to see agent list and packets
- Create a handoff from agent-a to agent-b
- Apply the handoff
- Click Agent B follow up to use the handed off memory

## Trust demo
Run Studio with an identity trust level.
Contributor lets you propose.
Approver lets you approve.
Owner can change trust rules and system rules.

Example commands
```
N3_IDENTITY_TRUST_LEVEL=contributor n3 examples/demo_ai_assistant_over_records.ai studio
N3_IDENTITY_TRUST_LEVEL=approver n3 examples/demo_ai_assistant_over_records.ai studio
N3_IDENTITY_TRUST_LEVEL=owner n3 examples/demo_ai_assistant_over_records.ai studio
```

## Try this
1. Click Memory tour
2. Open the Traces panel and select Plain view
3. Confirm memory_write items include meta.event_type, meta.importance_reason, and meta.authority
4. Confirm memory_write items include meta.space, meta.owner, and meta.lane
5. Confirm memory_promoted shows from_space, to_space, and ids
6. Confirm memory_promotion_denied shows a stable reason
7. Confirm memory_conflict includes winner and loser ids and rule
8. Confirm memory_denied shows a redacted attempted item and reason
9. Confirm memory_deleted shows conflict_loser and promoted reasons
10. Confirm memory_phase_started shows phase_id and reason
11. Confirm memory_phase_diff shows added, deleted, and replaced counts
12. Confirm memory_team_summary shows team lane changes
13. Confirm memory_proposed appears for team proposals
14. Confirm memory_approved appears after approval
15. Confirm memory_rejected appears after rejection
16. Confirm memory_agreement_summary reports approvals and rejections
17. Confirm memory_trust_check shows allowed and blocked actions
18. Confirm memory_approval_recorded shows approval counts
19. Confirm memory_trust_rules shows the trust rules
20. Confirm memory_rule_applied shows a rule decision
21. Confirm memory_rules_snapshot shows the active rule list
22. Open Rules and confirm the rule sentence is active
23. Pick a memory event and click Explain
24. Click Links for a memory event
25. Click Path to see the because trail
26. Click Impact to see impact lines and impact path
27. Look for memory_change_preview before memory_deleted or memory_promoted
28. Open Handoff and create a packet from agent-a to agent-b
29. Confirm memory_handoff_created appears in Traces
30. Apply the handoff and confirm memory_handoff_applied appears
31. Confirm memory_agent_briefing shows the briefing lines
32. Run Budget demo and confirm memory_budget appears
33. Confirm memory_compaction appears with action and reason
34. Run Cache demo and confirm memory_cache_miss then memory_cache_hit
35. Open the Memory budget section and read the budget lines
36. Stop Studio and run it again in the same folder
37. Confirm memory_wake_up_report shows restored memory lines
