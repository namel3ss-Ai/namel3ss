export type CitationEntry = {
  chunk_id?: string;
  document_id?: string;
  index: number;
  page?: number | string;
  page_number?: number | string;
  snippet?: string;
  source_id?: string;
  title: string;
  url?: string;
};

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function citationPage(entry: CitationEntry): string {
  const pageValue = entry.page_number ?? entry.page;
  if (typeof pageValue === "number" && Number.isFinite(pageValue)) {
    return String(Math.trunc(pageValue));
  }
  if (typeof pageValue === "string" && pageValue.trim()) {
    return pageValue.trim();
  }
  return "";
}

export function normalizeCitationEntries(raw: unknown): CitationEntry[] {
  const entries = Array.isArray(raw) ? raw : [];
  const normalized: CitationEntry[] = [];
  entries.forEach((entry, idx) => {
    if (!entry || typeof entry !== "object") {
      return;
    }
    const value = entry as Record<string, unknown>;
    const payload: CitationEntry = {
      index:
        typeof value.index === "number" && Number.isFinite(value.index)
          ? Math.max(1, Math.trunc(value.index))
          : idx + 1,
      title: text(value.title) || "Source",
    };
    const url = text(value.url);
    const sourceId = text(value.source_id);
    const snippet = text(value.snippet);
    const chunkId = text(value.chunk_id);
    const documentId = text(value.document_id);
    if (url) payload.url = url;
    if (sourceId) payload.source_id = sourceId;
    if (snippet) payload.snippet = snippet;
    if (chunkId) payload.chunk_id = chunkId;
    if (documentId) payload.document_id = documentId;
    if (typeof value.page === "number" || typeof value.page === "string") payload.page = value.page as number | string;
    if (typeof value.page_number === "number" || typeof value.page_number === "string") {
      payload.page_number = value.page_number as number | string;
    }
    normalized.push(payload);
  });
  return normalized;
}

export function citationIdentity(entry: CitationEntry): string {
  return [
    text(entry.title),
    text(entry.source_id),
    text(entry.url),
    text(entry.chunk_id),
    text(entry.document_id),
    citationPage(entry),
  ].join("|");
}

export function dedupeCitations(entries: CitationEntry[]): CitationEntry[] {
  const seen = new Set<string>();
  const values: CitationEntry[] = [];
  entries.forEach((entry) => {
    const key = citationIdentity(entry);
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    values.push(entry);
  });
  return values;
}

export function chipAriaLabel(entry: CitationEntry): string {
  const page = citationPage(entry);
  if (page) {
    return `Open source ${entry.index}: ${entry.title}, page ${page}`;
  }
  return `Open source ${entry.index}: ${entry.title}`;
}

export function shouldHideCitationRow(entries: CitationEntry[]): boolean {
  return entries.length === 0;
}
