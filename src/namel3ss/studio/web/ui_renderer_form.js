(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function formatConstraint(constraint) {
    const kind = constraint && constraint.kind;
    if (!kind) return "";
    if (kind === "present") return "required";
    if (kind === "unique") return "unique";
    if (kind === "integer") return "integer";
    if (kind === "pattern") return `pattern: ${constraint.value}`;
    if (kind === "greater_than") return `> ${constraint.value}`;
    if (kind === "at_least") return `≥ ${constraint.value}`;
    if (kind === "less_than") return `< ${constraint.value}`;
    if (kind === "at_most") return `≤ ${constraint.value}`;
    if (kind === "length_min") return `min length ${constraint.value}`;
    if (kind === "length_max") return `max length ${constraint.value}`;
    if (kind === "between") return `between ${constraint.min} and ${constraint.max}`;
    return String(kind);
  }

  function renderFormField(field, fieldErrors) {
    const row = document.createElement("div");
    row.className = "ui-form-field";

    const label = document.createElement("label");
    label.textContent = field.name || "Field";

    const input = document.createElement("input");
    input.name = field.name || "";
    if (field.readonly) {
      input.readOnly = true;
      input.classList.add("readonly");
    }
    label.appendChild(input);
    row.appendChild(label);

    if (field.help) {
      const help = document.createElement("div");
      help.className = "ui-form-help";
      help.textContent = field.help;
      row.appendChild(help);
    }

    const constraints = Array.isArray(field.constraints) ? field.constraints : [];
    if (constraints.length) {
      const hints = constraints.map(formatConstraint).filter(Boolean);
      if (hints.length) {
        const hint = document.createElement("div");
        hint.className = "ui-form-constraints";
        hint.textContent = hints.join(" · ");
        row.appendChild(hint);
      }
    }

    const error = document.createElement("div");
    error.className = "ui-form-error";
    row.appendChild(error);
    if (field.name) {
      fieldErrors.set(field.name, error);
    }

    return { row, input };
  }

  function renderFormElement(el, handleAction) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element";

    const formTitle = document.createElement("div");
    formTitle.className = "inline-label";
    formTitle.textContent = `Form: ${el.record}`;
    wrapper.appendChild(formTitle);

    const form = document.createElement("form");
    form.className = "ui-form";
    const fields = Array.isArray(el.fields) ? el.fields : [];
    const groups = Array.isArray(el.groups) ? el.groups : [];
    const fieldMap = new Map(fields.map((field) => [field.name, field]));
    const rendered = new Set();
    const fieldInputs = new Map();
    const fieldErrors = new Map();

    function renderFieldName(name, container) {
      const field = fieldMap.get(name);
      if (!field || rendered.has(name)) return;
      const renderedField = renderFormField(field, fieldErrors);
      rendered.add(name);
      if (field.name) fieldInputs.set(field.name, renderedField.input);
      container.appendChild(renderedField.row);
    }

    if (groups.length) {
      groups.forEach((group) => {
        const groupWrap = document.createElement("div");
        groupWrap.className = "ui-form-group";
        if (group.label) {
          const title = document.createElement("div");
          title.className = "ui-form-group-title";
          title.textContent = group.label;
          groupWrap.appendChild(title);
        }
        (group.fields || []).forEach((name) => renderFieldName(name, groupWrap));
        form.appendChild(groupWrap);
      });
      fields.forEach((field) => renderFieldName(field.name, form));
    } else {
      fields.forEach((field) => renderFieldName(field.name, form));
    }

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
      fieldInputs.forEach((input, name) => {
        values[name] = input ? input.value : "";
      });
      fieldErrors.forEach((node) => (node.textContent = ""));
      errors.textContent = "";
      const result = await handleAction({ id: el.action_id, type: "submit_form" }, { values });
      if (!result || result.ok) return;
      if (Array.isArray(result.errors)) {
        result.errors.forEach((err) => {
          const fieldError = fieldErrors.get(err.field);
          if (fieldError) fieldError.textContent = err.message || "Invalid value.";
        });
        errors.textContent = result.errors.map((err) => `${err.field}: ${err.message}`).join("; ");
        return;
      }
      if (result.error) {
        errors.textContent = result.error;
      }
    };

    wrapper.appendChild(form);
    return wrapper;
  }

  root.renderFormElement = renderFormElement;
})();
