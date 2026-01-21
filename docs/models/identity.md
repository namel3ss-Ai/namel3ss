# Identity

Identity defines who is calling the engine and what they can access.

**Example**
```ai
identity "user":
  field "subject" is text must be present
  field "roles" is json
  field "permissions" is json
  field "trust_level" is text must be present
  trust_level is one of ["guest", "member", "admin"]

flow "admin": requires has_role("admin")
```

**Notes**
- Roles and permissions accept lists; `identity.role` still works.
- Use `has_role` and `has_permission` in requires clauses.

**Command**
- `n3 explain --why`
