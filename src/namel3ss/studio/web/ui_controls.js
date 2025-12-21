function renderInspector(element, pageName) {
  const body = document.getElementById("inspectorBody");
  if (!body) return;
  body.innerHTML = "";
  if (!element) {
    showEmpty(body, "Select an element to inspect.");
    return;
  }
  const rows = document.createElement("div");
  rows.className = "inspector-body";
  const fields = [
    ["Type", element.type],
    ["Element ID", element.element_id],
    ["Page", pageName],
  ];
  if (element.action_id) {
    fields.push(["Action ID", element.action_id]);
  }
  if (element.action && element.action.flow) {
    fields.push(["Flow", element.action.flow]);
  }
  fields.forEach(([k, v]) => {
    const row = document.createElement("div");
    row.className = "kv-row";
    row.innerHTML = `<div>${k}</div><div>${v || ""}</div>`;
    rows.appendChild(row);
  });
  body.appendChild(rows);
  if (["title", "text", "button"].includes(element.type)) {
    const field = document.createElement("div");
    field.className = "field";
    const label = document.createElement("label");
    label.textContent = "Edit value";
    const input = document.createElement(element.type === "text" ? "textarea" : "input");
    input.value = element.value || element.label || "";
    const button = document.createElement("button");
    button.className = "btn secondary small";
    button.textContent = "Save";
    button.onclick = () => {
      const op = element.type === "title" ? "set_title" : element.type === "text" ? "set_text" : "set_button_label";
      performEdit(op, element.element_id, pageName, input.value);
    };
    field.appendChild(label);
    field.appendChild(input);
    field.appendChild(button);
    body.appendChild(field);
  }
}

function findElementInManifest(elementId) {
  if (!cachedManifest) return null;
  for (const page of cachedManifest.pages || []) {
    const found = _findElementRecursive(page.elements || [], elementId);
    if (found) return { element: found, page: page.name };
  }
  return null;
}
function _findElementRecursive(elements, elementId) {
  for (const el of elements) {
    if (el.element_id === elementId) return el;
    const nested = _findElementRecursive(el.children || [], elementId);
    if (nested) return nested;
  }
  return null;
}

function defaultSpec(type) {
  const spec = { type };
  if (type === "title") spec.value = "Title";
  if (type === "text") spec.value = "Text";
  if (type === "button") {
    spec.label = "Button";
    const action = Object.values(cachedManifest?.actions || {}).find((a) => a.type === "call_flow");
    spec.flow = action?.flow || "flow";
  }
  if (type === "form" || type === "table") {
    const action = Object.values(cachedManifest?.actions || {}).find((a) => a.type === "submit_form");
    if (action?.record) spec.record = action.record;
  }
  if (type === "section") spec.label = "Section";
  if (type === "card") spec.label = "Card";
  if (type === "row") spec.children = [{ type: "column", children: [{ type: "text", value: "Text" }] }];
  if (type === "column") spec.children = [{ type: "text", value: "Text" }];
  if (type === "divider") spec.type = "divider";
  if (type === "image") spec.src = "https://example.com/image.png";
  return spec;
}

function findTargetForInsert() {
  if (!cachedManifest) return null;
  if (selectedElementId && selectedPage) {
    return { page: selectedPage, element_id: selectedElementId };
  }
  const page = cachedManifest.pages && cachedManifest.pages[0];
  if (!page) return null;
  const last = page.elements && page.elements[page.elements.length - 1];
  if (!last) return null;
  return { page: page.name, element_id: last.element_id };
}

function setupInsertMoveControls() {
  const addBtn = document.getElementById("addElementButton");
  if (addBtn) {
    addBtn.onclick = () => {
      const select = document.getElementById("addElementSelect");
      const type = select ? select.value : "text";
      const target = findTargetForInsert();
      if (!target) {
        showToast("Select a target element first.");
        return;
      }
      const spec = defaultSpec(type);
      const containerTypes = ["section", "card", "row", "column"];
      const position = selectedElement && containerTypes.includes(selectedElement.type) ? "inside_end" : "after";
      performEdit("insert", target.element_id, target.page, spec, { position });
    };
  }
  const up = document.getElementById("moveUp");
  if (up) {
    up.onclick = () => {
      if (!selectedElementId) {
        showToast("Select an element to move.");
        return;
      }
      performEdit("move_up", selectedElementId, selectedPage || "", "");
    };
  }
  const down = document.getElementById("moveDown");
  if (down) {
    down.onclick = () => {
      if (!selectedElementId) {
        showToast("Select an element to move.");
        return;
      }
      performEdit("move_down", selectedElementId, selectedPage || "", "");
    };
  }
}

setupInsertMoveControls();

refreshAll();
