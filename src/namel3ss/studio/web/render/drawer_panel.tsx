import type { CitationEntry } from "./citation_chips";

export type DrawerTab = "sources" | "preview" | "explain";

export type DrawerState = {
  activeTab: DrawerTab;
  isOpen: boolean;
  selectedCitationKey: string;
};

export function defaultDrawerState(): DrawerState {
  return {
    activeTab: "sources",
    isOpen: false,
    selectedCitationKey: "",
  };
}

export function citationKey(entry: CitationEntry): string {
  const source = typeof entry.source_id === "string" ? entry.source_id.trim() : "";
  const doc = typeof entry.document_id === "string" ? entry.document_id.trim() : "";
  const chunk = typeof entry.chunk_id === "string" ? entry.chunk_id.trim() : "";
  const page =
    typeof entry.page_number === "number" || typeof entry.page_number === "string"
      ? String(entry.page_number)
      : typeof entry.page === "number" || typeof entry.page === "string"
        ? String(entry.page)
        : "";
  return [entry.title, source, doc, chunk, page].join("|");
}

export function openDrawerForCitation(state: DrawerState, entry: CitationEntry): DrawerState {
  return {
    activeTab: "sources",
    isOpen: true,
    selectedCitationKey: citationKey(entry),
  };
}

export function selectCitationFromList(state: DrawerState, entry: CitationEntry): DrawerState {
  return {
    ...state,
    activeTab: "preview",
    isOpen: true,
    selectedCitationKey: citationKey(entry),
  };
}

export function setDrawerTab(state: DrawerState, tab: DrawerTab): DrawerState {
  return {
    ...state,
    activeTab: tab,
  };
}

export function closeDrawer(state: DrawerState): DrawerState {
  return {
    ...state,
    isOpen: false,
  };
}

export function shouldTrapDrawerFocus(isMobileViewport: boolean): boolean {
  return isMobileViewport;
}
