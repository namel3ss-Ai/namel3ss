(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

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

  function textValue(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function buildBasicPreviewPageUrl(target) {
    const entry = target && typeof target === "object" ? target : {};
    const documentId = textValue(entry.document_id || entry.documentId || entry.doc_id);
    if (!documentId) {
      return "";
    }
    const pageNumber = toPageNumber(entry.page_number || entry.page);
    const chunkId = textValue(entry.chunk_id || entry.source_id);
    const path = `/api/documents/${encodeURIComponent(documentId)}/pages/${pageNumber}`;
    if (!chunkId) {
      return path;
    }
    return `${path}?chunk_id=${encodeURIComponent(chunkId)}`;
  }

  root.buildBasicPreviewPageUrl = buildBasicPreviewPageUrl;
})();
