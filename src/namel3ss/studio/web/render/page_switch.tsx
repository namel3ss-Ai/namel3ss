export type PageEntry = {
  name: string;
  slug: string;
};

export function resolvePageSlug(value: string, pages: PageEntry[]): string {
  if (!value) return "";
  for (const entry of pages) {
    if (entry.slug === value || entry.name === value) return entry.slug;
  }
  return "";
}

export function selectInitialPage(params: {
  pages: PageEntry[];
  activeSlug: string;
  routeSlug: string;
  currentSelection: string;
}): string {
  const pages = params.pages || [];
  const selectedActive = resolvePageSlug(params.activeSlug, pages);
  if (selectedActive) return selectedActive;
  const selectedRoute = resolvePageSlug(params.routeSlug, pages);
  if (selectedRoute) return selectedRoute;
  const selectedCurrent = resolvePageSlug(params.currentSelection, pages);
  if (selectedCurrent) return selectedCurrent;
  return pages.length ? pages[0].slug : "";
}
