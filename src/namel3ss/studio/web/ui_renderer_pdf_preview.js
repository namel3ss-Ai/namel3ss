(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function textValue(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function toPageNumber(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      const parsed = Math.trunc(value);
      return parsed > 0 ? parsed : 1;
    }
    if (typeof value === "string" && value.trim() && /^\d+$/.test(value.trim())) {
      const parsed = Number.parseInt(value.trim(), 10);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
    }
    return 1;
  }

  function buildCitationDeepLinkQuery(entry) {
    const payload = entry && typeof entry === "object" ? entry : {};
    const docId = textValue(payload.document_id || payload.doc_id || payload.documentId);
    const pageNumber = toPageNumber(payload.page_number || payload.page);
    const citationId = textValue(payload.citation_id || payload.citationId);
    const params = new URLSearchParams();
    params.set("doc", docId);
    params.set("page", String(pageNumber));
    params.set("cit", citationId);
    return params.toString();
  }

  function parseCitationDeepLink(search) {
    const source = typeof search === "string" ? search : window.location.search;
    const query = source.startsWith("?") ? source.slice(1) : source;
    const params = new URLSearchParams(query);
    const docId = textValue(params.get("doc"));
    const pageNumber = toPageNumber(params.get("page"));
    const citationId = textValue(params.get("cit"));
    return {
      citation_id: citationId,
      document_id: docId,
      page_number: pageNumber,
    };
  }

  function applyCitationDeepLinkState(entry) {
    if (!window.history || typeof window.history.replaceState !== "function") {
      return;
    }
    const query = buildCitationDeepLinkQuery(entry);
    if (!query) return;
    const url = `${window.location.pathname}?${query}${window.location.hash || ""}`;
    window.history.replaceState(window.history.state, "", url);
  }

  function buildPdfPreviewRequestUrl(documentId, pageNumber, chunkId, citationId) {
    const docId = textValue(documentId);
    if (!docId) return "";
    const params = new URLSearchParams();
    const chunkText = textValue(chunkId);
    const citationText = textValue(citationId);
    if (chunkText) params.set("chunk_id", chunkText);
    if (citationText) params.set("citation_id", citationText);
    const query = params.toString();
    const path = `/api/documents/${encodeURIComponent(docId)}/pages/${toPageNumber(pageNumber)}`;
    return query ? `${path}?${query}` : path;
  }

  function citationColorIndex(citationId, paletteSize) {
    const input = textValue(citationId);
    const size = Number.isFinite(paletteSize) && paletteSize > 0 ? Math.trunc(paletteSize) : 8;
    if (!input) return 0;
    let hash = 0;
    for (let i = 0; i < input.length; i += 1) {
      hash = (hash * 33 + input.charCodeAt(i)) >>> 0;
    }
    return hash % size;
  }

  root.buildCitationDeepLinkQuery = buildCitationDeepLinkQuery;
  root.parseCitationDeepLink = parseCitationDeepLink;
  root.applyCitationDeepLinkState = applyCitationDeepLinkState;
  root.buildPdfPreviewRequestUrl = buildPdfPreviewRequestUrl;
  root.citationColorIndex = citationColorIndex;
})();
