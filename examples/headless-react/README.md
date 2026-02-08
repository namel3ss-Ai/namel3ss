# Headless React Example

Minimal example for rendering a Namel3ss app via `/api/v1/*` using `@namel3ss/ui-client`.

## Run

1. Start runtime:
   - `n3 run app.ai --headless --api-token dev-token --cors-origin http://localhost:5173`
2. In your React app:
   - install client package
   - create the client with the same token

```js
import { Namel3ssUiClient } from "@namel3ss/ui-client";

const client = new Namel3ssUiClient("http://127.0.0.1:8787", {
  apiVersion: "v1",
  apiToken: "dev-token"
});
```

See `App.jsx` for a basic manifest/action loop.
