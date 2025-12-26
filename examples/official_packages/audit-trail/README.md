# audit-trail

Audit helpers, log views, and tamper-evident history patterns.

## Install

```
n3 pkg add github:namel3ss-ai/audit-trail@v0.1.0
```

## Usage

```
use "audit-trail" as audit

page "home":
  button "Record audit":
    calls flow "audit.record_event"
  table is "audit.AuditEntry"
```

## Development

```
n3 pkg validate .
n3 test
n3 verify --prod
```
