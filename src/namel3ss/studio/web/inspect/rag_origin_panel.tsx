export type RagOriginInfo = {
  base: string;
  features: string[];
  region: string;
  slot?: string;
};

export function extractRagOrigin(origin: Record<string, unknown> | null | undefined): RagOriginInfo | null {
  if (!origin || typeof origin !== "object") return null;
  const raw = (origin as { rag_ui?: unknown }).rag_ui;
  if (!raw || typeof raw !== "object") return null;
  const base = typeof (raw as { base?: unknown }).base === "string" ? String((raw as { base?: unknown }).base) : "";
  const region =
    typeof (raw as { region?: unknown }).region === "string" ? String((raw as { region?: unknown }).region) : "";
  const slot = typeof (raw as { slot?: unknown }).slot === "string" ? String((raw as { slot?: unknown }).slot) : "";
  const featuresRaw = (raw as { features?: unknown }).features;
  const features = Array.isArray(featuresRaw)
    ? featuresRaw.map((entry) => String(entry)).filter((entry) => entry)
    : [];
  if (!base || !region) return null;
  const info: RagOriginInfo = { base, features, region };
  if (slot) info.slot = slot;
  return info;
}

export function formatRagOrigin(info: RagOriginInfo | null): string {
  if (!info) return "";
  const features = info.features.length ? `features: ${info.features.join(", ")}` : "features: none";
  const slot = info.slot ? `slot: ${info.slot}` : "";
  return ["rag_ui", `base: ${info.base}`, `region: ${info.region}`, features, slot].filter(Boolean).join(" · ");
}
