(() => {
  const root = window.N3UIRender || {};

  function _formatBytes(value) {
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
      return "";
    }
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }

  function _isSupportedPreview(file) {
    const type = typeof file.type === "string" ? file.type.toLowerCase() : "";
    return type.startsWith("image/") || type.startsWith("text/") || type === "application/pdf";
  }

  function _previewSummary(file) {
    const type = typeof file.type === "string" ? file.type.toLowerCase() : "";
    const preview = file.preview && typeof file.preview === "object" ? file.preview : {};
    if (type.startsWith("image/")) {
      return `Image preview ready (${file.name || "file"}).`;
    }
    if (type === "application/pdf") {
      const pages = typeof preview.page_count === "number" ? preview.page_count : null;
      if (pages !== null) return `PDF preview ready (${pages} pages).`;
      return "PDF preview ready.";
    }
    if (type.startsWith("text/")) {
      const lines = typeof preview.item_count === "number" ? preview.item_count : null;
      if (lines !== null) return `Text preview ready (${lines} lines).`;
      return "Text preview ready.";
    }
    return "Preview not available.";
  }

  async function _uploadFile(file, uploadName) {
    const filename = file && file.name ? file.name : uploadName || "upload";
    const response = await fetch(`/api/upload?name=${encodeURIComponent(filename)}`, {
      method: "POST",
      headers: { "Content-Type": (file && file.type) || "application/octet-stream" },
      body: file,
    });
    const payload = await response.json();
    if (!response.ok || !payload || payload.ok === false || !payload.upload) {
      const message =
        (payload && payload.error && (payload.error.message || payload.error.error)) || "Upload failed.";
      throw new Error(message);
    }
    return payload.upload;
  }

  function renderUploadElement(el, handleAction) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element ui-upload";
    wrapper.dataset.uploadName = typeof el.name === "string" ? el.name : "";

    const header = document.createElement("div");
    header.className = "ui-upload-header";
    const title = document.createElement("div");
    title.className = "ui-upload-title";
    title.textContent = typeof el.label === "string" && el.label ? el.label : "Upload";
    header.appendChild(title);
    if (el.required === true) {
      const badge = document.createElement("span");
      badge.className = "ui-upload-required";
      badge.textContent = "Required";
      header.appendChild(badge);
    }
    wrapper.appendChild(header);

    const controls = document.createElement("div");
    controls.className = "ui-upload-controls";
    const chooseButton = document.createElement("button");
    chooseButton.type = "button";
    chooseButton.className = "btn small";
    chooseButton.textContent = typeof el.label === "string" && el.label ? el.label : "Upload";
    const disabled = el.enabled === false || el.disabled === true;
    chooseButton.disabled = disabled;
    controls.appendChild(chooseButton);
    wrapper.appendChild(controls);

    const input = document.createElement("input");
    input.type = "file";
    input.className = "ui-upload-input";
    input.hidden = true;
    if (Array.isArray(el.accept) && el.accept.length) {
      input.accept = el.accept.join(",");
    }
    input.multiple = el.multiple === true;
    input.disabled = disabled;
    wrapper.appendChild(input);

    const status = document.createElement("div");
    status.className = "ui-upload-status";
    status.textContent = disabled ? "Uploads are disabled." : "No upload in progress.";
    wrapper.appendChild(status);

    const filesSection = document.createElement("div");
    filesSection.className = "ui-upload-files";
    wrapper.appendChild(filesSection);

    const previewSection = document.createElement("div");
    previewSection.className = "ui-upload-preview";
    wrapper.appendChild(previewSection);

    const clearActionId = typeof el.clear_action_id === "string" ? el.clear_action_id : "";
    const selectActionId = typeof el.action_id === "string" ? el.action_id : typeof el.id === "string" ? el.id : "";

    async function removeFile(uploadId, opener) {
      if (!clearActionId) return;
      await handleAction(
        {
          id: clearActionId,
          type: "upload_clear",
        },
        uploadId ? { upload_id: uploadId } : {},
        opener
      );
    }

    function renderSelectedFiles() {
      filesSection.innerHTML = "";
      previewSection.innerHTML = "";
      const files = Array.isArray(el.files) ? el.files.filter((entry) => entry && typeof entry === "object") : [];
      if (!files.length) {
        const empty = document.createElement("div");
        empty.className = "ui-upload-empty";
        empty.textContent = "No files selected.";
        filesSection.appendChild(empty);
        return;
      }
      const list = document.createElement("div");
      list.className = "ui-upload-file-list";
      files.forEach((file) => {
        const item = document.createElement("div");
        item.className = "ui-upload-file-item";
        const meta = document.createElement("div");
        meta.className = "ui-upload-file-meta";
        const name = typeof file.name === "string" && file.name ? file.name : "file";
        const size = _formatBytes(file.size);
        meta.textContent = size ? `${name} (${size})` : name;
        item.appendChild(meta);
        if (clearActionId) {
          const removeButton = document.createElement("button");
          removeButton.type = "button";
          removeButton.className = "btn small ghost";
          removeButton.textContent = "Remove";
          const uploadId =
            (typeof file.id === "string" && file.id) ||
            (typeof file.checksum === "string" && file.checksum) ||
            null;
          removeButton.onclick = async (event) => {
            event.preventDefault();
            removeButton.disabled = true;
            try {
              await removeFile(uploadId, event.currentTarget);
            } finally {
              removeButton.disabled = false;
            }
          };
          item.appendChild(removeButton);
        }
        list.appendChild(item);
        if (el.preview === true) {
          const previewItem = document.createElement("div");
          previewItem.className = "ui-upload-preview-item";
          previewItem.textContent = _isSupportedPreview(file) ? _previewSummary(file) : "Preview not available.";
          previewSection.appendChild(previewItem);
        }
      });
      filesSection.appendChild(list);
      if (clearActionId && files.length > 1) {
        const clearAll = document.createElement("button");
        clearAll.type = "button";
        clearAll.className = "btn small ghost ui-upload-clear-all";
        clearAll.textContent = "Clear all";
        clearAll.onclick = async (event) => {
          event.preventDefault();
          clearAll.disabled = true;
          try {
            await removeFile(null, event.currentTarget);
          } finally {
            clearAll.disabled = false;
          }
        };
        filesSection.appendChild(clearAll);
      }
    }

    chooseButton.onclick = (event) => {
      event.preventDefault();
      if (disabled) return;
      input.click();
    };

    input.onchange = async () => {
      const files = Array.from(input.files || []);
      if (!files.length || !selectActionId) return;
      chooseButton.disabled = true;
      status.classList.remove("is-error");
      try {
        for (let index = 0; index < files.length; index += 1) {
          status.textContent = `Uploading ${index + 1}/${files.length}...`;
          const metadata = await _uploadFile(files[index], el.name);
          await handleAction(
            {
              id: selectActionId,
              type: "upload_select",
            },
            { upload: metadata },
            chooseButton
          );
        }
        status.textContent = "Upload complete.";
      } catch (error) {
        status.classList.add("is-error");
        status.textContent = error && error.message ? error.message : "Upload failed.";
      } finally {
        chooseButton.disabled = disabled;
        input.value = "";
      }
    };

    renderSelectedFiles();
    return wrapper;
  }

  root.renderUploadElement = renderUploadElement;
  window.N3UIRender = root;
})();
