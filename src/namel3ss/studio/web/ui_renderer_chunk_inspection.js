(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function textValue(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function intValue(value, fallback) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return Math.trunc(value);
    }
    if (typeof value === "string" && /^\d+$/.test(value.trim())) {
      return Number.parseInt(value.trim(), 10);
    }
    return fallback;
  }

  function buildPreviewUrl(entry) {
    if (entry && typeof entry.preview_url === "string" && entry.preview_url.trim()) {
      return entry.preview_url.trim();
    }
    const docId = textValue(entry && (entry.doc_id || entry.document_id));
    const pageNumber = Math.max(1, intValue(entry && (entry.page_number || entry.page), 1));
    const chunkId = textValue(entry && (entry.chunk_id || entry.source_id));
    if (!docId) {
      return "";
    }
    const path = `/api/documents/${encodeURIComponent(docId)}/pages/${pageNumber}`;
    if (!chunkId) {
      return path;
    }
    return `${path}?chunk_id=${encodeURIComponent(chunkId)}`;
  }

  function openChunkPreview(entry, button) {
    const payload = {
      title: textValue(entry.source_name) || textValue(entry.doc_id) || "Chunk source",
      snippet: textValue(entry.snippet),
      chunk_id: textValue(entry.chunk_id),
      document_id: textValue(entry.doc_id),
      page_number: intValue(entry.page_number, 1),
      source_id: textValue(entry.chunk_id),
      url: buildPreviewUrl(entry),
    };
    if (typeof root.openCitationPreview === "function") {
      root.openCitationPreview(payload, button, [payload]);
      return;
    }
    const targetUrl = payload.url;
    if (targetUrl) {
      window.open(targetUrl, "_blank", "noopener,noreferrer");
    }
  }

  function renderPages(container, pages) {
    container.textContent = "";
    if (!Array.isArray(pages) || !pages.length) {
      const empty = document.createElement("div");
      empty.className = "ui-chunk-inspector-empty";
      empty.textContent = "No parsed pages loaded.";
      container.appendChild(empty);
      return;
    }
    pages.forEach((page) => {
      const item = document.createElement("div");
      item.className = "ui-chunk-inspector-page";
      const label = document.createElement("div");
      label.className = "ui-chunk-inspector-page-label";
      label.textContent = `Page ${Math.max(1, intValue(page && page.page_number, 1))}`;
      const snippet = document.createElement("div");
      snippet.className = "ui-chunk-inspector-page-snippet";
      snippet.textContent = textValue(page && page.snippet) || "No page text.";
      item.appendChild(label);
      item.appendChild(snippet);
      container.appendChild(item);
    });
  }

  async function fetchInspection(documentId) {
    const params = new URLSearchParams();
    if (documentId) {
      params.set("document_id", documentId);
    }
    const query = params.toString();
    const path = query ? `/api/chunks/inspection?${query}` : "/api/chunks/inspection";
    const response = await fetch(path, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error(`Chunk inspection request failed (${response.status}).`);
    }
    const payload = await response.json();
    if (!payload || typeof payload !== "object" || payload.ok !== true || !payload.chunk_inspection) {
      throw new Error("Chunk inspection payload is invalid.");
    }
    return payload.chunk_inspection;
  }

  function renderChunkInspectorTable(tbody, rows) {
    tbody.textContent = "";
    const entries = Array.isArray(rows) ? rows : [];
    if (!entries.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 7;
      cell.className = "ui-chunk-inspector-empty";
      cell.textContent = "No chunks found.";
      row.appendChild(cell);
      tbody.appendChild(row);
      return;
    }
    entries.forEach((entry) => {
      const row = document.createElement("tr");
      row.className = "ui-chunk-inspector-row";

      const docCell = document.createElement("td");
      docCell.textContent = textValue(entry.doc_id);
      row.appendChild(docCell);

      const indexCell = document.createElement("td");
      indexCell.textContent = String(Math.max(0, intValue(entry.chunk_index, 0)));
      row.appendChild(indexCell);

      const pageCell = document.createElement("td");
      pageCell.textContent = String(Math.max(1, intValue(entry.page_number, 1)));
      row.appendChild(pageCell);

      const signatureCell = document.createElement("td");
      signatureCell.className = "ui-chunk-inspector-signature";
      signatureCell.textContent = textValue(entry.boundary_signature);
      row.appendChild(signatureCell);

      const snippetCell = document.createElement("td");
      snippetCell.className = "ui-chunk-inspector-snippet";
      snippetCell.textContent = textValue(entry.snippet) || "No snippet.";
      row.appendChild(snippetCell);

      const linkCell = document.createElement("td");
      const link = document.createElement("code");
      link.textContent = textValue(entry.deep_link_query);
      linkCell.appendChild(link);
      row.appendChild(linkCell);

      const actionCell = document.createElement("td");
      const openButton = document.createElement("button");
      openButton.type = "button";
      openButton.className = "btn small ghost";
      openButton.textContent = "Open page";
      openButton.onclick = () => openChunkPreview(entry, openButton);
      actionCell.appendChild(openButton);
      row.appendChild(actionCell);

      tbody.appendChild(row);
    });
  }

  function renderChunkInspectorElement(el) {
    const payload = el && typeof el === "object" ? el : {};
    const wrapper = document.createElement("div");
    wrapper.className = "ui-chunk-inspector";

    const title = document.createElement("div");
    title.className = "ui-chunk-inspector-title";
    title.textContent = textValue(payload.title) || "Chunk inspector";
    wrapper.appendChild(title);

    const controls = document.createElement("div");
    controls.className = "ui-chunk-inspector-controls";
    const documentSelect = document.createElement("select");
    documentSelect.className = "ui-chunk-inspector-select";
    controls.appendChild(documentSelect);
    const refreshButton = document.createElement("button");
    refreshButton.type = "button";
    refreshButton.className = "btn small ghost";
    refreshButton.textContent = "Refresh";
    controls.appendChild(refreshButton);
    wrapper.appendChild(controls);

    const table = document.createElement("table");
    table.className = "ui-chunk-inspector-table";
    const thead = document.createElement("thead");
    thead.innerHTML =
      "<tr><th>Doc</th><th>Chunk</th><th>Page</th><th>Boundary</th><th>Snippet</th><th>Deep link</th><th>Action</th></tr>";
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    table.appendChild(tbody);
    wrapper.appendChild(table);

    const pagesTitle = document.createElement("div");
    pagesTitle.className = "ui-chunk-inspector-pages-title";
    pagesTitle.textContent = "Parsed pages";
    wrapper.appendChild(pagesTitle);
    const pages = document.createElement("div");
    pages.className = "ui-chunk-inspector-pages";
    wrapper.appendChild(pages);

    const status = document.createElement("div");
    status.className = "ui-chunk-inspector-status";
    wrapper.appendChild(status);

    let activePayload = payload && payload.chunk_inspection ? payload.chunk_inspection : payload;

    function normalizeDocuments(nextPayload) {
      const rows = Array.isArray(nextPayload && nextPayload.documents) ? nextPayload.documents : [];
      return rows.filter((row) => row && typeof row === "object");
    }

    function applyPayload(nextPayload) {
      activePayload = nextPayload && typeof nextPayload === "object" ? nextPayload : {};
      const rows = Array.isArray(activePayload.rows) ? activePayload.rows : [];
      const docs = normalizeDocuments(activePayload);
      const activeDocumentId = textValue(activePayload.document_id);

      documentSelect.textContent = "";
      const allOption = document.createElement("option");
      allOption.value = "";
      allOption.textContent = "All documents";
      allOption.selected = !activeDocumentId;
      documentSelect.appendChild(allOption);
      docs.forEach((doc) => {
        const option = document.createElement("option");
        option.value = textValue(doc.doc_id);
        option.textContent = `${textValue(doc.source_name) || option.value} (${Math.max(
          0,
          intValue(doc.chunk_count, 0)
        )})`;
        option.selected = option.value === activeDocumentId;
        documentSelect.appendChild(option);
      });

      renderChunkInspectorTable(tbody, rows);
      renderPages(pages, activePayload.pages);
      const totalCount = Math.max(0, intValue(activePayload.total_count, rows.length));
      status.textContent = `Showing ${rows.length} of ${totalCount} chunks.`;
    }

    async function refresh(documentId) {
      status.textContent = "Loading chunks...";
      refreshButton.disabled = true;
      documentSelect.disabled = true;
      try {
        const nextPayload = await fetchInspection(documentId);
        applyPayload(nextPayload);
      } catch (error) {
        status.textContent = error && error.message ? error.message : "Unable to load chunk inspection.";
      } finally {
        refreshButton.disabled = false;
        documentSelect.disabled = false;
      }
    }

    documentSelect.onchange = () => {
      const docId = textValue(documentSelect.value);
      refresh(docId);
    };
    refreshButton.onclick = () => {
      const docId = textValue(documentSelect.value);
      refresh(docId);
    };

    applyPayload(activePayload);
    if (!Array.isArray(activePayload.rows) || !activePayload.rows.length) {
      refresh(textValue(activePayload.document_id));
    }
    return wrapper;
  }

  root.renderChunkInspectorElement = renderChunkInspectorElement;
})();
