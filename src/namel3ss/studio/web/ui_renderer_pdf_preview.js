(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});
  const DEEP_LINK_DOC_KEY = "n3_doc";
  const DEEP_LINK_PAGE_KEY = "n3_doc_page";
  const DEEP_LINK_CIT_KEY = "n3_cit";
  const DEEP_LINK_CHUNK_KEY = "n3_chunk";

  function textValue(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function toPageNumber(value, fallback = 1) {
    if (typeof value === "number" && Number.isFinite(value)) {
      const parsed = Math.trunc(value);
      return parsed > 0 ? parsed : fallback;
    }
    if (typeof value === "string" && value.trim() && /^\d+$/.test(value.trim())) {
      const parsed = Number.parseInt(value.trim(), 10);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
    }
    return fallback;
  }

  function buildCitationDeepLinkQuery(entry) {
    const payload = entry && typeof entry === "object" ? entry : {};
    const docId = textValue(payload.document_id || payload.doc_id || payload.documentId);
    const pageNumber = toPageNumber(payload.page_number || payload.page);
    const citationId = textValue(payload.citation_id || payload.citationId);
    const chunkId = textValue(payload.chunk_id || payload.chunkId);
    if (!docId && !citationId) return "";
    const params = new URLSearchParams();
    if (docId) {
      params.set(DEEP_LINK_DOC_KEY, docId);
      params.set(DEEP_LINK_PAGE_KEY, String(pageNumber));
    }
    if (citationId) params.set(DEEP_LINK_CIT_KEY, citationId);
    if (chunkId) params.set(DEEP_LINK_CHUNK_KEY, chunkId);
    return params.toString();
  }

  function parseCitationDeepLink(search) {
    const source = typeof search === "string" ? search : window.location.search;
    const query = source.startsWith("?") ? source.slice(1) : source;
    const params = new URLSearchParams(query);
    const docId = textValue(params.get(DEEP_LINK_DOC_KEY)) || textValue(params.get("doc"));
    const pageText =
      textValue(params.get(DEEP_LINK_PAGE_KEY)) || textValue(params.get("doc_page")) || textValue(params.get("n3_page"));
    let pageNumber = toPageNumber(pageText, 0);
    if (!pageNumber && docId) {
      // Backward compatibility for legacy ?doc=...&page=<number>&cit=...
      const legacyPage = textValue(params.get("page"));
      pageNumber = toPageNumber(legacyPage, 0);
    }
    if (!pageNumber && docId) pageNumber = 1;
    const citationId =
      textValue(params.get(DEEP_LINK_CIT_KEY)) || textValue(params.get("citation_id")) || textValue(params.get("cit"));
    const chunkId = textValue(params.get(DEEP_LINK_CHUNK_KEY)) || textValue(params.get("chunk_id"));
    return {
      citation_id: citationId,
      chunk_id: chunkId,
      document_id: docId,
      page_number: pageNumber,
    };
  }

  function applyCitationDeepLinkState(entry) {
    if (!window.history || typeof window.history.replaceState !== "function") {
      return;
    }
    const payload = entry && typeof entry === "object" ? entry : {};
    const docId = textValue(payload.document_id || payload.doc_id || payload.documentId);
    const pageNumber = toPageNumber(payload.page_number || payload.page);
    const citationId = textValue(payload.citation_id || payload.citationId);
    const chunkId = textValue(payload.chunk_id || payload.chunkId);
    if (!docId && !citationId) return;
    const url = new URL(window.location.href);
    // Remove legacy keys to avoid collisions with route page selection.
    url.searchParams.delete("doc");
    url.searchParams.delete("cit");
    url.searchParams.delete("chunk_id");
    if (docId) {
      url.searchParams.set(DEEP_LINK_DOC_KEY, docId);
      url.searchParams.set(DEEP_LINK_PAGE_KEY, String(pageNumber));
    } else {
      url.searchParams.delete(DEEP_LINK_DOC_KEY);
      url.searchParams.delete(DEEP_LINK_PAGE_KEY);
    }
    if (citationId) {
      url.searchParams.set(DEEP_LINK_CIT_KEY, citationId);
    } else {
      url.searchParams.delete(DEEP_LINK_CIT_KEY);
    }
    if (chunkId) {
      url.searchParams.set(DEEP_LINK_CHUNK_KEY, chunkId);
    } else {
      url.searchParams.delete(DEEP_LINK_CHUNK_KEY);
    }
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
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
