# Editor

The Editor service gives fast, local language features for namel3ss projects.

Start the editor service (from your project root):
```bash
n3 editor
```

Pick a port explicitly:
```bash
n3 editor --port 7333
```

## VS Code extension (minimal client)

Install the extension from this repo:
- Open VS Code.
- Run `Developer: Install Extension from Location...`
- Select `extensions/vscode`.

Configure the port if needed:
- Setting: `n3.editor.serverPort` (default 7333)

## Features
- Diagnostics on save
- Hover summaries
- Go-to-definition
- Safe rename
- Quick fixes

The Editor is local, fast, and never prints secret values.
