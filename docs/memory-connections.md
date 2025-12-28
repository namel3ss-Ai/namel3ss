# Memory Connections

Memory can show simple links between items.
Links are deterministic and trace backed.
Links are created only from real events.

## Link types
- depends_on
- caused_by
- replaced
- promoted_from
- conflicts_with
- supports

## How links are created
- replaced links are created when an item replaces another item
- promoted_from links are created when a promotion happens
- conflicts_with links are created when a conflict happens
- caused_by links are created when a tool call caused a write
- phase diff can add replaced links when needed
- denied writes do not create links

## Link preview
- each link stores a short preview of the target text
- previews are redacted and stable
- previews remove bracket characters

## Paths
- a path is a short because trail for one item
- paths are deterministic and capped at six lines

## Studio
- Open Studio
- Open Traces
- Pick a memory event
- Click Links to see link lines
- Click Path to see the path
