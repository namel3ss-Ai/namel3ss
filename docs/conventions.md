# Conventions

This file explains the route conventions that keep APIs consistent and easy to use.

## Error envelope

Every route error is returned as the same shape:

- `code`
- `message`
- `remediation`

This keeps client behavior predictable across routes.

## Pagination

List responses use the same query parameters:

- `page` starts at 1
- `page_size` sets how many items to return

List responses should include `next_page` when more results are available.

Pagination is configured in `.namel3ss/conventions.yaml`.

## Filtering

Filtering uses a single query parameter named `filter`.

Format:
- `field:value` pairs separated by commas

Allowed fields are listed in `.namel3ss/conventions.yaml`.

## Response formats

Routes return JSON by default.

If a route allows the `toon` format, clients can request it using:

- `format=toon` in the query string
- or an `Accept` header that includes the word `toon`

Allowed formats are configured in `.namel3ss/formats.yaml`.

## Example config files

Conventions config:

```
defaults:
  pagination: true
  page_size_default: 50
  page_size_max: 200
routes:
  list_users:
    filter_fields:
      - status
      - role
```

Formats config:

```
routes:
  list_users:
    - json
    - toon
```
