# Concurrency

Parallel runs tasks in a flow in a deterministic way.
Order is stable.
Tasks join at the end of the block.

## Syntax
parallel:
  run "alpha":
    let alpha_total is 10 + 5
    return alpha_total
  run "beta":
    let beta_total is 8 * 2
    return beta_total

## Rules
- Task names are unique
- Tasks run in name order
- Tasks may read state
- Tasks may not write state
- Tasks may write local variables only
- Tool calls must be pure
- AI calls must keep deterministic trace order
- Record writes are blocked
- Theme changes are blocked
- Nested parallel blocks are blocked

## Results
Task results merge into a list in task name order.
Local updates merge in task name order.
Conflicts raise a clear error.

## Traces
Traces include parallel started, task finished, and merge summaries.

## Studio
Studio traces show parallel blocks and task summaries.
Filters let you hide or show parallel events.

## Capability id
runtime.concurrency

## See also
- [Engine model (runtime)](runtime.md) — execution model and flow execution.
- [Execution how](execution-how.md) — explainable execution and flow inspection.
