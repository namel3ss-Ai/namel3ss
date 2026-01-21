# Authentication Example

Single-concept example: create a session and call a protected flow.

How to use it:
- copy this folder to a new project directory
- set `N3_AUTH_ALLOW_IDENTITY=1`
- run `n3 app.ai check`
- run `n3 run` and open the browser
- click "Run protected flow" to see the guidance error
- in the browser console, run:

```js
fetch("/api/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    identity: {
      subject: "demo-user",
      roles: ["admin"],
      permissions: ["reports.view"],
      trust_level: "member"
    }
  })
});
```

- click "Run protected flow" again to see access granted

Optional: set `N3_AUTH_SIGNING_KEY=demo-key` and add `issue_token: true` to the login body to receive a bearer token.
