export type NavigationItem = {
  label: string;
  targetSlug: string;
  active: boolean;
};

export function normalizeNavigationItems(input: unknown): NavigationItem[] {
  if (!Array.isArray(input)) return [];
  const items: NavigationItem[] = [];
  for (const entry of input) {
    if (!entry || typeof entry !== "object") continue;
    const candidate = entry as Record<string, unknown>;
    const targetSlug = typeof candidate.target_slug === "string" ? candidate.target_slug.trim() : "";
    if (!targetSlug) continue;
    const label = typeof candidate.label === "string" && candidate.label.trim() ? candidate.label.trim() : targetSlug;
    items.push({
      label,
      targetSlug,
      active: candidate.active === true,
    });
  }
  return items;
}

export function findActiveNavigationTarget(items: NavigationItem[], fallbackSlug: string): string {
  const active = items.find((entry) => entry.active);
  if (active) return active.targetSlug;
  return fallbackSlug;
}
