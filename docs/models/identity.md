# Identity

Identity defines who is calling the engine and what they can access.

**Example**
```ai
identity "User":
  field "role" is text must be present

flow "admin": requires identity.role is "admin"
```

**Command**
- `n3 explain --why`
