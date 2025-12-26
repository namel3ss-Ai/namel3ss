# Verify

Verify is the governance check: access rules, package integrity, determinism, and capability policy.

**Example**
```ai
flow "create": requires identity.role is "admin"
  return "ok"
```

**Command**
- `n3 verify --prod`
