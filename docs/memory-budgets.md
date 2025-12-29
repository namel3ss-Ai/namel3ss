# Memory budgets

Memory budgets keep memory fast and small.
A budget sets soft limits for each space, lane, and phase.
When memory is near a limit, the system records a budget event.

## Budget actions
- The system can compact low value items into one summary item
- The system can remove low value items without a summary
- The system can deny a write when nothing safe can be removed
- Each action includes a clear reason code

## Compaction
Compaction replaces many low value items with one summary item.
The summary keeps safe preview lines and a compact ledger.
Links, paths, and impact still work after compaction.

## Cache
Recall caching stores the recall result for a space, lane, and phase.
The cache key also includes the store key to keep owners and agent lanes separate.
The cache key uses a stable fingerprint of the query and policy.
Cache entries are evicted in a stable order.
Cache events show when a hit or miss happens.

## Studio view
Open the Traces panel.
Open a trace and look for the Memory budget section.
Use the memory filters to show budget, compaction, and cache events.

## Persistence
Budgets and cache settings are saved with memory.
Restore keeps the same budget configs.
Wake up report lines show cache status.

## Protected items
System lane rules are protected.
Team decisions are protected.
Pending proposals are protected.
Approved items are protected unless policy allows changes.
