# Identity

Identity defines who is calling the engine and what they can access.

**Example**
```ai
identity "user":
  fields:
    subject is text must be present
    roles is json
    permissions is json
    trust_level is text must be present
  trust_level is one of "guest", "member", "admin"

flow "admin": requires has_role("admin")
```

**Notes**
- Roles and permissions accept lists; `identity.role` still works.
- Use `has_role` and `has_permission` in requires clauses.
- Legacy `field "name" is <type>` lines are also accepted.

**Command**
- `n3 explain --why`
