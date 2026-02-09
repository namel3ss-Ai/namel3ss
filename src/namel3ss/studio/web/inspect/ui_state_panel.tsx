export type UIStatePanelRow = {
  path: string;
  key: string;
  scope: "ephemeral" | "session" | "persistent";
  typeName: string;
  source: "default" | "restored";
  value: unknown;
};

type UIStateFieldEntry = {
  key: string;
  path: string;
  scope: "ephemeral" | "session" | "persistent";
  type: string;
  source: "default" | "restored";
};

const SCOPE_ORDER: Array<"ephemeral" | "session" | "persistent"> = ["ephemeral", "session", "persistent"];

export function buildUIStatePanelRows(input: unknown): UIStatePanelRow[] {
  if (!input || typeof input !== "object") return [];
  const payload = input as Record<string, unknown>;
  const fieldsRaw = payload.fields;
  const valuesRaw = payload.values;
  const valuesByScope = valuesRaw && typeof valuesRaw === "object" ? (valuesRaw as Record<string, unknown>) : {};
  if (!Array.isArray(fieldsRaw)) return [];
  const rows: UIStatePanelRow[] = [];
  for (const scope of SCOPE_ORDER) {
    for (const entry of fieldsRaw) {
      const field = normalizeFieldEntry(entry);
      if (!field || field.scope !== scope) continue;
      const scopeValuesRaw = valuesByScope[scope];
      const scopeValues = scopeValuesRaw && typeof scopeValuesRaw === "object" ? (scopeValuesRaw as Record<string, unknown>) : {};
      rows.push({
        path: field.path,
        key: field.key,
        scope: field.scope,
        typeName: field.type,
        source: field.source,
        value: scopeValues[field.key],
      });
    }
  }
  return rows;
}

export function formatUIStatePanelValue(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value, null, 2);
  } catch (_err) {
    return "<unserializable>";
  }
}

function normalizeFieldEntry(entry: unknown): UIStateFieldEntry | null {
  if (!entry || typeof entry !== "object") return null;
  const raw = entry as Record<string, unknown>;
  const key = typeof raw.key === "string" ? raw.key.trim() : "";
  const path = typeof raw.path === "string" ? raw.path.trim() : "";
  const scope = normalizeScope(raw.scope);
  const type = typeof raw.type === "string" ? raw.type.trim() : "";
  const source = raw.source === "restored" ? "restored" : "default";
  if (!key || !path || !scope || !type) return null;
  return { key, path, scope, type, source };
}

function normalizeScope(value: unknown): "ephemeral" | "session" | "persistent" | null {
  if (value === "ephemeral" || value === "session" || value === "persistent") return value;
  return null;
}
