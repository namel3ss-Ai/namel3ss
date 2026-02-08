import { useEffect, useMemo, useState } from "react";
import { Namel3ssUiClient } from "@namel3ss/ui-client";

export default function App() {
  const client = useMemo(
    () =>
      new Namel3ssUiClient("http://127.0.0.1:8787", {
        apiVersion: "v1",
        apiToken: "dev-token"
      }),
    []
  );
  const [manifest, setManifest] = useState(null);
  const [actions, setActions] = useState([]);

  useEffect(() => {
    let mounted = true;
    async function load() {
      const nextManifest = await client.getManifest();
      const nextActions = await client.getActions();
      if (!mounted) {
        return;
      }
      setManifest(nextManifest);
      setActions(Array.isArray(nextActions?.actions) ? nextActions.actions : []);
    }
    load().catch(console.error);
    return () => {
      mounted = false;
    };
  }, [client]);

  return (
    <main>
      <h1>Headless Namel3ss</h1>
      <pre>{JSON.stringify(manifest, null, 2)}</pre>
      {actions.slice(0, 1).map((action) => (
        <button
          key={action.id}
          onClick={async () => {
            await client.runAction(action.id, {});
            const nextManifest = await client.getManifest();
            setManifest(nextManifest);
          }}
        >
          Run {action.id}
        </button>
      ))}
    </main>
  );
}
