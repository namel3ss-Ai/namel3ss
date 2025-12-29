# Memory packs

Memory packs let you reuse memory setup across projects.
A pack stores structure only.
No personal memory data is included.

## What a pack contains
- Rules as short sentences
- Trust settings
- Agreement defaults
- Budget settings
- Lane defaults
- Phase defaults

## Where packs live
Packs live under packs memory in the project root.
Each pack is a folder with pack.toml or pack.yaml.
Rules can be listed in pack rules or in rules.txt.

## Merge order
System defaults are the base.
Packs load in a stable order by folder name.
Later packs override earlier packs.
Local overrides override packs.
Rules append in pack order.
Duplicate rules keep the last source.

## Local overrides
Local overrides live under dot namel3ss as memory_overrides.toml or memory_overrides.yaml.
Overrides must be explicit.
Overrides are traced.

## Restore and packs
Packs load at startup.
Pack rules are applied after restore.
If packs change, rules update to match.

## Studio
Studio shows the active packs.
Studio shows what is overridden.
Trace events show pack load and merge.

## Protected scope
Packs do not include personal memory data.
Pack rules are read only by default.

## Capability id
runtime.memory_packs
