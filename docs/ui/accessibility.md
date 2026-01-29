# Accessibility contract

## Scope
Accessibility is a required UX contract. It is deterministic, validated, and explainable.

## Roles and labels
- Interactive elements emit roles by default.
- Accessible names are derived deterministically from labels, titles, placeholders, or record field names.
- Forms and tables always carry deterministic labels for fields and columns.

## Keyboard and focus behavior
- Tab order follows deterministic source order.
- Modals and drawers move focus into the overlay on open, contain focus while open, and return focus to the opener on close.
- Overlays are dismissible with the Escape key.
- Tabs expose deterministic active selection and keyboard navigation contracts.

## Contrast validation
- Theme and accent combinations are validated against a contrast-safe contract.
- Unsafe combinations are rejected during static validation.
- No styling DSL is required to satisfy the contrast contract.

## Explain and CI enforcement
- Explain output includes accessibility metadata (role, label, focus/keyboard markers).
- CI enforces accessibility determinism through fixtures and validation checks.
