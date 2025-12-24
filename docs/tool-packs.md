# Tool packs

Tool packs are built-in Python tools that ship with namel3ss. They require no extra
dependencies and run without external installs.

To use a pack, declare a tool in `app.ai` and bind it in `.namel3ss/tools.yaml` (or use `n3 tools bind`).

Example:
```ai
tool "slugify text":
  implemented using python

  input:
    text is text
    separator is optional text

  output:
    text is text
```

```yaml
# .namel3ss/tools.yaml
tools:
  "slugify text":
    kind: "python"
    entry: "namel3ss.tool_packs.text:slugify"
```

## http
Suggested bindings:
- "get json from web" -> `namel3ss.tool_packs.http:get_json`
- "post json to web" -> `namel3ss.tool_packs.http:post_json`

Payloads:
- `get_json`: `{ "url": "...", "headers"?: { "X-Token": "..." }, "timeout_seconds"?: 10 }`
- `post_json`: `{ "url": "...", "data": {...}, "headers"?: {...}, "timeout_seconds"?: 10 }`

## datetime
Suggested bindings:
- "current time" -> `namel3ss.tool_packs.datetime:now`
- "parse datetime" -> `namel3ss.tool_packs.datetime:parse`
- "format datetime" -> `namel3ss.tool_packs.datetime:format`
- "add days to datetime" -> `namel3ss.tool_packs.datetime:add_days`

Payloads:
- `now`: `{ "timezone"?: "utc" | "local" }`
- `parse`: `{ "text": "...", "format"?: "%Y-%m-%d" }`
- `format`: `{ "iso": "...", "format": "%Y-%m-%d" }`
- `add_days`: `{ "iso": "...", "days": 3 }`

## text
Suggested bindings:
- "slugify text" -> `namel3ss.tool_packs.text:slugify`
- "tokenize text" -> `namel3ss.tool_packs.text:tokenize`
- "lowercase text" -> `namel3ss.tool_packs.text:lower`
- "uppercase text" -> `namel3ss.tool_packs.text:upper`
- "trim text" -> `namel3ss.tool_packs.text:trim`

Payloads:
- `slugify`: `{ "text": "...", "separator"?: "-" }`
- `tokenize`: `{ "text": "...", "delimiter"?: " " }`
- `lower`/`upper`/`trim`: `{ "text": "..." }`

## file
Suggested bindings:
- "read text file" -> `namel3ss.tool_packs.file:read_text`
- "write text file" -> `namel3ss.tool_packs.file:write_text`
- "read json file" -> `namel3ss.tool_packs.file:read_json`
- "write json file" -> `namel3ss.tool_packs.file:write_json`

Payloads:
- `read_text`: `{ "path": "data/file.txt", "encoding"?: "utf-8" }`
- `write_text`: `{ "path": "data/file.txt", "text": "...", "encoding"?: "utf-8", "create_dirs"?: true }`
- `read_json`: `{ "path": "data/file.json", "encoding"?: "utf-8" }`
- `write_json`: `{ "path": "data/file.json", "data": {...}, "encoding"?: "utf-8", "create_dirs"?: true }`

## math
Suggested bindings:
- "mean" -> `namel3ss.tool_packs.math:mean`
- "median" -> `namel3ss.tool_packs.math:median`
- "describe numbers" -> `namel3ss.tool_packs.math:describe`

Payloads:
- `mean`/`median`/`describe`: `{ "values": [1, 2, 3] }`

## Example
```ai
tool "slugify text":
  implemented using python

  input:
    text is text

  output:
    text is text

flow "demo":
  let result is slugify text:
    text is "Hello World"
  return result
```

```yaml
# .namel3ss/tools.yaml
tools:
  "slugify text":
    kind: "python"
    entry: "namel3ss.tool_packs.text:slugify"
```
