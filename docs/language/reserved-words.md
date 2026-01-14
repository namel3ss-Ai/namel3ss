# Reserved words in namel3ss

Some words are part of the language and UI DSL and cannot be reused as variable names.

Reserved words keep the grammar clear, align with the UI DSL, and protect deterministic execution.

To avoid collisions, prefix names with your domain context, for example:
- `ticket_title`
- `article_title`
- `item_type`

To see the canonical list:
```bash
n3 reserved
```

Common collisions to avoid: `title`, `text`, `type`, `page`, `form`, `table`.
