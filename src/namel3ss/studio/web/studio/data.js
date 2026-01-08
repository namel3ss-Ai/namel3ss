(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const dataView = root.data || (root.data = {});

  function flattenElements(elements) {
    const list = [];
    (elements || []).forEach((element) => {
      list.push(element);
      if (Array.isArray(element.children)) {
        list.push(...flattenElements(element.children));
      }
    });
    return list;
  }

  function collectTables(manifest) {
    const tables = [];
    if (!manifest || !manifest.pages) return tables;
    manifest.pages.forEach((page) => {
      const elements = flattenElements(page.elements || []);
      elements.forEach((element) => {
        if (element.type === "table") tables.push(element);
      });
    });
    return tables;
  }

  function renderTable(table) {
    const section = document.createElement("section");
    section.className = "data-section";

    const heading = document.createElement("div");
    heading.className = "data-title";
    heading.textContent = table.record || "Table";
    section.appendChild(heading);

    const wrap = document.createElement("div");
    wrap.className = "data-table-wrap";
    const htmlTable = document.createElement("table");
    htmlTable.className = "ui-table data-table";

    const columns = Array.isArray(table.columns) ? table.columns : [];
    const rows = Array.isArray(table.rows) ? table.rows : [];
    const pageSize = table.pagination && Number.isInteger(table.pagination.page_size) ? table.pagination.page_size : null;
    const displayRows = pageSize ? rows.slice(0, pageSize) : rows;
    if (!columns.length) {
      wrap.appendChild(dom.buildEmpty("No columns available."));
      section.appendChild(wrap);
      return section;
    }

    const header = document.createElement("tr");
    columns.forEach((column) => {
      const th = document.createElement("th");
      th.textContent = column.label || column.name;
      header.appendChild(th);
    });
    htmlTable.appendChild(header);

    if (!displayRows.length) {
      const empty = document.createElement("div");
      empty.className = "data-empty";
      empty.textContent = table.empty_text || "No rows yet.";
      wrap.appendChild(empty);
      section.appendChild(wrap);
      return section;
    }

    displayRows.forEach((row) => {
      const tr = document.createElement("tr");
      columns.forEach((column) => {
        const td = document.createElement("td");
        td.textContent = row[column.name] ?? "";
        tr.appendChild(td);
      });
      htmlTable.appendChild(tr);
    });

    wrap.appendChild(htmlTable);
    section.appendChild(wrap);
    return section;
  }

  function renderData(nextManifest) {
    const container = document.getElementById("data");
    if (!container) return;
    container.innerHTML = "";
    const manifest = nextManifest || state.getCachedManifest();
    if (!manifest) {
      dom.showEmpty(container, "No data yet. Run your app.");
      return;
    }
    const tables = collectTables(manifest);
    if (!tables.length) {
      dom.showEmpty(container, "No tables available.");
      return;
    }
    tables.forEach((table) => {
      container.appendChild(renderTable(table));
    });
  }

  dataView.renderData = renderData;
  window.renderData = renderData;
})();
