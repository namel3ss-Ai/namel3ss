let renderUI = (manifest) => {
  const select = document.getElementById("pageSelect");
  const uiContainer = document.getElementById("ui");
  const pages = manifest.pages || [];
  const emptyMessage = "Run your app to see it here.";
  if (!uiContainer) return;
  const currentSelection = select ? select.value : "";
  if (select) {
    select.innerHTML = "";
    pages.forEach((p, idx) => {
      const opt = document.createElement("option");
      opt.value = p.name;
      opt.textContent = p.name;
      if (p.name === currentSelection || (currentSelection === "" && idx === 0)) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
  }
  function renderChildren(container, children, pageName) {
    (children || []).forEach((child) => {
      const node = renderElement(child, pageName);
      container.appendChild(node);
    });
  }
  function renderElement(el, pageName) {
    if (!el) return document.createElement("div");
    if (el.type === "section") {
      const section = document.createElement("div");
      section.className = "ui-element ui-section";
      if (el.label) {
        const header = document.createElement("div");
        header.className = "ui-section-title";
        header.textContent = el.label;
        section.appendChild(header);
      }
      renderChildren(section, el.children, pageName);
      return section;
    }
    if (el.type === "card") {
      const card = document.createElement("div");
      card.className = "ui-element ui-card";
      if (el.label) {
        const header = document.createElement("div");
        header.className = "ui-card-title";
        header.textContent = el.label;
        card.appendChild(header);
      }
      renderChildren(card, el.children, pageName);
      return card;
    }
    if (el.type === "row") {
      const row = document.createElement("div");
      row.className = "ui-row";
      renderChildren(row, el.children, pageName);
      return row;
    }
    if (el.type === "column") {
      const col = document.createElement("div");
      col.className = "ui-column";
      renderChildren(col, el.children, pageName);
      return col;
    }
    if (el.type === "divider") {
      const hr = document.createElement("hr");
      hr.className = "ui-divider";
      return hr;
    }
    if (el.type === "image") {
      const wrapper = document.createElement("div");
      wrapper.className = "ui-element ui-image-wrapper";
      const img = document.createElement("img");
      img.className = "ui-image";
      img.src = el.src || "";
      img.alt = el.alt || "";
      img.loading = "lazy";
      wrapper.appendChild(img);
      return wrapper;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element";
    if (el.type === "title") {
      const h = document.createElement("h3");
      h.textContent = el.value;
      wrapper.appendChild(h);
    } else if (el.type === "text") {
      const value = typeof el.value === "string" ? el.value : String(el.value || "");
      if (value.startsWith("$ ")) {
        const pre = document.createElement("pre");
        pre.className = "n3-codeblock";
        pre.textContent = value;
        wrapper.appendChild(pre);
      } else {
        const p = document.createElement("p");
        p.textContent = value;
        wrapper.appendChild(p);
      }
    } else if (el.type === "button") {
      const actions = document.createElement("div");
      actions.className = "ui-buttons";
      const btn = document.createElement("button");
      btn.className = "btn primary";
      btn.textContent = el.label;
      btn.onclick = (e) => {
        e.stopPropagation();
        executeAction(el.action_id, {});
      };
      actions.appendChild(btn);
      wrapper.appendChild(actions);
    } else if (el.type === "form") {
      const formTitle = document.createElement("div");
      formTitle.className = "inline-label";
      formTitle.textContent = `Form: ${el.record}`;
      wrapper.appendChild(formTitle);
      const form = document.createElement("form");
      form.className = "ui-form";
      (el.fields || []).forEach((f) => {
        const label = document.createElement("label");
        label.textContent = f.name;
        const input = document.createElement("input");
        input.name = f.name;
        label.appendChild(input);
        form.appendChild(label);
      });
      const submit = document.createElement("button");
      submit.type = "submit";
      submit.className = "btn primary";
      submit.textContent = "Submit";
      form.appendChild(submit);
      const errors = document.createElement("div");
      errors.className = "errors";
      form.appendChild(errors);
      form.onsubmit = async (e) => {
        e.preventDefault();
        const values = {};
        (el.fields || []).forEach((f) => {
          const input = form.querySelector(`input[name="${f.name}"]`);
          values[f.name] = input ? input.value : "";
        });
        const result = await executeAction(el.action_id, { values });
        if (!result.ok && result.errors) {
          errors.textContent = result.errors.map((err) => `${err.field}: ${err.message}`).join("; ");
        } else if (!result.ok && result.error) {
          errors.textContent = result.error;
        } else {
          errors.textContent = "";
        }
      };
      wrapper.appendChild(form);
    } else if (el.type === "table") {
      const table = document.createElement("table");
      table.className = "ui-table";
      const header = document.createElement("tr");
      (el.columns || []).forEach((c) => {
        const th = document.createElement("th");
        th.textContent = c.name;
        header.appendChild(th);
      });
      table.appendChild(header);
      (el.rows || []).forEach((row) => {
        const tr = document.createElement("tr");
        (el.columns || []).forEach((c) => {
          const td = document.createElement("td");
          td.textContent = row[c.name] ?? "";
          tr.appendChild(td);
        });
        table.appendChild(tr);
      });
      wrapper.appendChild(table);
    }
    return wrapper;
  }
  function renderPage(pageName) {
    uiContainer.innerHTML = "";
    const page = pages.find((p) => p.name === pageName) || pages[0];
    if (!page) {
      showEmpty(uiContainer, emptyMessage);
      return;
    }
    page.elements.forEach((el) => {
      uiContainer.appendChild(renderElement(el, page.name));
    });
  }
  if (select) {
    select.onchange = (e) => renderPage(e.target.value);
  }
  const initialPage = (select && select.value) || (pages[0] ? pages[0].name : "");
  if (initialPage) {
    renderPage(initialPage);
  } else {
    showEmpty(uiContainer, emptyMessage);
  }
};

let renderUIError = (detail) => {
  const select = document.getElementById("pageSelect");
  const uiContainer = document.getElementById("ui");
  const emptyMessage = "Run your app to see it here.";
  if (!uiContainer) return;
  if (select) select.innerHTML = "";
  if (typeof showError === "function") {
    showError(uiContainer, detail);
  } else if (typeof showEmpty === "function") {
    showEmpty(uiContainer, emptyMessage);
  }
};

window.renderUI = renderUI;
window.renderUIError = renderUIError;
