let renderUI = (manifest) => {
  const select = document.getElementById("pageSelect");
  const uiContainer = document.getElementById("ui");
  const pages = manifest.pages || [];
  const currentSelection = select.value;
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
  function renderChildren(container, children, pageName) {
    (children || []).forEach((child) => {
      const node = renderElement(child, pageName);
      container.appendChild(node);
    });
  }
  function attachSelection(node, el, pageName) {
    node.dataset.elementId = el.element_id;
    node.onclick = (e) => {
      e.stopPropagation();
      window.selectElementFromUI(el, pageName, node);
    };
  }
  function makeEditable(textEl, el, pageName, op) {
    textEl.classList.add("editable");
    textEl.onclick = (e) => {
      e.stopPropagation();
      if (textEl.classList.contains("editing")) return;
      textEl.classList.add("editing");
      const input = document.createElement(el.type === "text" ? "textarea" : "input");
      input.value = el.value || el.label || "";
      input.className = "inline-input";
      textEl.replaceWith(input);
      input.focus();
      const cancel = () => {
        input.replaceWith(textEl);
        textEl.classList.remove("editing");
      };
      input.onkeydown = (ev) => {
        if (ev.key === "Escape") {
          cancel();
        }
        if (ev.key === "Enter" && ev.shiftKey === false && el.type !== "text") {
          ev.preventDefault();
          confirm();
        }
      };
      input.onblur = cancel;
      const confirm = () => {
        const newValue = input.value;
        cancel();
        window.requestEditValue(el, pageName, op, newValue);
      };
      input.onchange = confirm;
    };
  }
  function renderElement(el, pageName) {
    if (!el) return document.createElement("div");
    if (el.type === "section") {
      const section = document.createElement("div");
      section.className = "ui-element ui-section";
      attachSelection(section, el, pageName);
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
      attachSelection(card, el, pageName);
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
      attachSelection(row, el, pageName);
      renderChildren(row, el.children, pageName);
      return row;
    }
    if (el.type === "column") {
      const col = document.createElement("div");
      col.className = "ui-column";
      attachSelection(col, el, pageName);
      renderChildren(col, el.children, pageName);
      return col;
    }
    if (el.type === "divider") {
      const hr = document.createElement("hr");
      hr.className = "ui-divider";
      attachSelection(hr, el, pageName);
      return hr;
    }
    if (el.type === "image") {
      const wrapper = document.createElement("div");
      wrapper.className = "ui-element ui-image-wrapper";
      attachSelection(wrapper, el, pageName);
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
    attachSelection(wrapper, el, pageName);
    if (el.type === "title") {
      const h = document.createElement("h3");
      h.textContent = el.value;
      makeEditable(h, el, pageName, "set_title");
      wrapper.appendChild(h);
    } else if (el.type === "text") {
      const p = document.createElement("p");
      p.textContent = el.value;
      makeEditable(p, el, pageName, "set_text");
      wrapper.appendChild(p);
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
      const rename = document.createElement("button");
      rename.className = "btn ghost small editable";
      rename.textContent = el.label;
      makeEditable(rename, el, pageName, "set_button_label");
      actions.appendChild(btn);
      actions.appendChild(rename);
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
      showEmpty(uiContainer, "No pages");
      return;
    }
    page.elements.forEach((el) => {
      uiContainer.appendChild(renderElement(el, page.name));
    });
  }
  select.onchange = (e) => renderPage(e.target.value);
  const initialPage = select.value || (pages[0] ? pages[0].name : "");
  if (initialPage) {
    renderPage(initialPage);
  } else {
    showEmpty(uiContainer, "No pages");
  }
};

window.selectElementFromUI = (element, pageName, node) => {
  document.querySelectorAll(".ui-element").forEach((el) => el.classList.remove("selected"));
  if (node && node.classList) node.classList.add("selected");
  selectedElement = element;
  selectedPage = pageName;
  selectedElementId = element.element_id;
  renderInspector(element, pageName);
};

window.requestEditValue = (element, pageName, op, newValue) => {
  performEdit(op, element.element_id, pageName, newValue);
};
