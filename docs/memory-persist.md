# Memory persistence

Memory is saved to disk in the project folder.
The data lives in .namel3ss/memory under the project root.
The snapshot file is memory_snapshot.json.
The checksum file is memory_snapshot.sha256.

## When memory is written
Memory is written after a flow run commits.
Memory is written after agreement apply or reject.
Memory is written after rule changes.
Memory is written after handoff apply or reject.
Memory is written after phase changes and diff ledger updates.
Memory is written after compaction.

## Restore
On startup, if a snapshot exists, memory is restored.
If the snapshot is missing, memory starts fresh.
If restore fails, the run stops and explains why.
No partial memory is used.

## Wake up report
A wake up report trace is emitted after restore or fresh start.
It lists totals for items, rules, proposals, handoffs, and cache.
Studio shows the report in the Traces panel.

## Protection
Secrets are redacted before writing.
Only memory state is stored.

## Other memory files
The memory CLI writes a proof pack for recall and explain:
- `.namel3ss/memory/last.json`
- `.namel3ss/memory/last.plain`
- `.namel3ss/memory/last.why.txt`
- `.namel3ss/memory/last.graph.json`

These files are not used for persistence and can be deleted safely.
