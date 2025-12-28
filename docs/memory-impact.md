# Memory Impact

Impact shows what will be affected if a memory item changes.
Impact is based on links only.
No guessing is used.

## What impact means
- Impact follows link types depends_on, caused_by, supports, conflicts_with, replaced, promoted_from
- Direction rules are deterministic
- Impact depth is limited to two steps

## Impact lines
- Impact summary lists affected items and reasons
- Impact path shows the chain by depth

## Lane context
Impact follows the lane of the selected memory item.
Use the lane selector in Studio to focus on my lane or team lane.

## Request impact
- Set state._memory_impact_id to a memory id
- Run an AI call
- Clear the state key when done
- Optional state._memory_impact_depth can be 1 or 2
- Optional state._memory_impact_max_items can limit the list

## Change preview
- A change preview is emitted before a replace or promote action
- It lists the items that would be affected

## Studio
- Open Studio
- Open Traces
- Pick a memory event
- Click Impact
- Use Depth 1 or Depth 2
