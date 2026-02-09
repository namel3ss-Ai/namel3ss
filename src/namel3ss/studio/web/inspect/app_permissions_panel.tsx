export type AppPermissionUsageRow = {
  permission: string;
  reason: string;
  line: number | null;
  column: number | null;
};

export type AppPermissionsPanel = {
  enabled: boolean;
  mode: "explicit" | "legacy" | "none";
  usage: AppPermissionUsageRow[];
  warnings: string[];
};

export function buildAppPermissionsPanel(input: unknown): AppPermissionsPanel {
  if (!input || typeof input !== "object") {
    return { enabled: false, mode: "none", usage: [], warnings: [] };
  }
  const payload = input as Record<string, unknown>;
  const enabled = payload.enabled === true;
  const mode = normalizeMode(payload.mode, enabled);
  const usage = normalizeUsage(payload.usage);
  const warnings = normalizeWarnings(payload.warnings);
  return { enabled, mode, usage, warnings };
}

function normalizeMode(value: unknown, enabled: boolean): "explicit" | "legacy" | "none" {
  if (value === "explicit" || value === "legacy") return value;
  if (enabled) return "explicit";
  return "none";
}

function normalizeUsage(value: unknown): AppPermissionUsageRow[] {
  if (!Array.isArray(value)) return [];
  const rows: AppPermissionUsageRow[] = [];
  for (const entry of value) {
    if (!entry || typeof entry !== "object") continue;
    const raw = entry as Record<string, unknown>;
    const permission = typeof raw.permission === "string" ? raw.permission.trim() : "";
    const reason = typeof raw.reason === "string" ? raw.reason.trim() : "";
    if (!permission || !reason) continue;
    rows.push({
      permission,
      reason,
      line: typeof raw.line === "number" ? raw.line : null,
      column: typeof raw.column === "number" ? raw.column : null,
    });
  }
  rows.sort((a, b) => {
    if (a.permission < b.permission) return -1;
    if (a.permission > b.permission) return 1;
    if (a.reason < b.reason) return -1;
    if (a.reason > b.reason) return 1;
    if ((a.line ?? -1) !== (b.line ?? -1)) return (a.line ?? -1) - (b.line ?? -1);
    return (a.column ?? -1) - (b.column ?? -1);
  });
  return rows;
}

function normalizeWarnings(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  const rows = value
    .filter((entry): entry is string => typeof entry === "string")
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
  return Array.from(new Set(rows)).sort();
}
