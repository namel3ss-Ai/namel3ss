# Compatibility Policy

## Promise
Namel3ss treats compatibility as a product contract.

## Breaking Changes
A change is breaking if it:
- removes or renames an existing grammar/runtime/contract surface
- changes semantics for valid existing programs
- changes required response fields or field types

Breaking changes **must**:
1. Declare intent explicitly.
2. Include migration documentation.
3. Include explicit CI acknowledgment.
4. Bump the relevant version marker.

## Additive Changes
Allowed without breaking bump:
- optional response fields
- new capabilities that do not alter existing semantics
- documentation clarifications

## Forbidden Changes
- silent grammar drift
- silent contract drift
- hidden runtime behavior changes without spec updates
