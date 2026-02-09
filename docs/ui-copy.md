# Copy

What it checks: page titles, intro text, container labels, text length, and action labels.

## Warnings
- `copy.missing_page_title` - page has no title.
- `copy.missing_intro_text` - data-heavy content appears before any intro text.
- `copy.unlabeled_container` - sections, cards, tabs, drawers, or modals lack labels.
- `copy.duplicate_container_label` - labels repeat within a page.
- `copy.text_too_long` - text blocks are too long.
- `copy.action_label` - action labels are empty, too long, or not verb-led.

## Fix
Use short sentences, unique labels, and verb-first actions.

## Example
```ai
record "Ticket":
  id text

flow "create_ticket":
  return "ok"

page "home":
  title is "Support"
  text is "Triage tickets and reply with clarity."
  section "Queue":
    card "Inbox":
      table is "Ticket"
  button "Create ticket":
    calls flow "create_ticket"
```
