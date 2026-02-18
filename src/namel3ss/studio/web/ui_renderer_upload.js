(() => {
  const root = window.N3UIRender || {};

  function _uploadStateRegistry() {
    const registry = root.__uploadStateByName;
    if (!registry || typeof registry !== "object") {
      const next = {};
      root.__uploadStateByName = next;
      return next;
    }
    return registry;
  }

  function _composerUploadRegistry() {
    const registry = root.__hiddenComposerUploads;
    if (!registry || typeof registry !== "object") {
      return {};
    }
    return registry;
  }

  function _manifestComposerUploadRegistry() {
    const uploads = {};
    const studioRoot = window.N3Studio || {};
    const studioState = studioRoot && studioRoot.state ? studioRoot.state : null;
    const manifest =
      studioState && typeof studioState.getCachedManifest === "function" ? studioState.getCachedManifest() : null;

    function scan(value) {
      if (!value) return;
      if (Array.isArray(value)) {
        value.forEach((entry) => scan(entry));
        return;
      }
      if (typeof value !== "object") return;
      const type = typeof value.type === "string" ? value.type.trim().toLowerCase() : "";
      if (type === "chat") {
        const attach = typeof value.composer_attach_upload === "string" ? value.composer_attach_upload.trim() : "";
        if (attach) {
          uploads[attach] = true;
        }
      }
      for (const nested of Object.values(value)) {
        scan(nested);
      }
    }

    scan(manifest && manifest.pages);
    return uploads;
  }

  function _isComposerManagedUpload(uploadName) {
    const key = typeof uploadName === "string" ? uploadName.trim() : "";
    if (!key) return false;
    const registry = _composerUploadRegistry();
    if (registry[key] === true) {
      return true;
    }
    const manifestRegistry = _manifestComposerUploadRegistry();
    return manifestRegistry[key] === true;
  }

  function _normalizeUploadFile(file) {
    if (!file || typeof file !== "object") return null;
    const normalized = {};
    if (typeof file.id === "string" && file.id) normalized.id = file.id;
    if (typeof file.name === "string" && file.name) normalized.name = file.name;
    if (typeof file.type === "string" && file.type) normalized.type = file.type;
    if (typeof file.checksum === "string" && file.checksum) normalized.checksum = file.checksum;
    if (typeof file.size === "number" && Number.isFinite(file.size) && file.size >= 0) normalized.size = file.size;
    return normalized;
  }

  function _buildUploadStateSnapshot(el, uploadName, clearActionId, selectActionId) {
    const files = Array.isArray(el && el.files)
      ? el.files.map((entry) => _normalizeUploadFile(entry)).filter((entry) => entry && typeof entry === "object")
      : [];
    return {
      name: uploadName,
      label: typeof el.label === "string" ? el.label : "",
      files: files,
      clear_action_id: clearActionId,
      action_id: selectActionId,
    };
  }

  function _notifyUploadStateChanged(uploadName, snapshot) {
    if (!uploadName || typeof document === "undefined" || typeof document.dispatchEvent !== "function") return;
    if (typeof window !== "undefined" && typeof window.CustomEvent === "function") {
      document.dispatchEvent(new window.CustomEvent("n3:upload-state", { detail: { name: uploadName, snapshot: snapshot } }));
    }
  }

  function _setUploadStateSnapshot(wrapper, uploadName, snapshot) {
    const key = typeof uploadName === "string" ? uploadName.trim() : "";
    if (!key) return;
    const registry = _uploadStateRegistry();
    if (snapshot && typeof snapshot === "object") {
      registry[key] = snapshot;
    } else {
      delete registry[key];
    }
    if (wrapper && wrapper.dataset) {
      if (snapshot && typeof snapshot === "object") {
        try {
          wrapper.dataset.uploadState = JSON.stringify(snapshot);
        } catch (error) {
          delete wrapper.dataset.uploadState;
        }
      } else {
        delete wrapper.dataset.uploadState;
      }
    }
    _notifyUploadStateChanged(key, snapshot && typeof snapshot === "object" ? snapshot : null);
  }

  function getUploadStateSnapshot(uploadName) {
    const key = typeof uploadName === "string" ? uploadName.trim() : "";
    if (!key) return null;
    const registry = _uploadStateRegistry();
    const snapshot = registry[key];
    if (!snapshot || typeof snapshot !== "object") return null;
    return snapshot;
  }

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

  function _openUploadInputPicker(input) {
    if (!input || input.disabled === true) return false;
    const restoreHidden = input.hidden === true;
    if (restoreHidden) {
      input.hidden = false;
    }
    try {
      if (typeof input.showPicker === "function") {
        input.showPicker();
        return true;
      }
      if (typeof input.click === "function") {
        input.click();
        return true;
      }
    } catch (error) {
      try {
        if (typeof input.click === "function") {
          input.click();
          return true;
        }
      } catch (fallbackError) {
        return false;
      }
    } finally {
      if (restoreHidden) {
        input.hidden = true;
      }
    }
    return false;
  }

  function renderUploadElement(el, handleAction) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element ui-upload";
    const uploadName = typeof el.name === "string" ? el.name : "";
    wrapper.dataset.uploadName = uploadName;
    const hideSurface = el && el.hide_surface === true;
    if (hideSurface || _isComposerManagedUpload(uploadName)) {
      wrapper.classList.add("ui-upload-hidden-surface");
    }

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
    input.tabIndex = -1;
    input.setAttribute("aria-hidden", "true");
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
    _setUploadStateSnapshot(wrapper, uploadName, _buildUploadStateSnapshot(el, uploadName, clearActionId, selectActionId));

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
      _setUploadStateSnapshot(wrapper, uploadName, _buildUploadStateSnapshot(el, uploadName, clearActionId, selectActionId));
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
      _openUploadInputPicker(input);
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
        const postAction =
          input.__n3UploadPickerPostAction && typeof input.__n3UploadPickerPostAction === "object"
            ? input.__n3UploadPickerPostAction
            : null;
        if (postAction && typeof postAction.id === "string" && postAction.id) {
          status.textContent = "Upload complete. Refreshing...";
          const actionPayload =
            postAction.payload && typeof postAction.payload === "object" ? { ...postAction.payload } : {};
          await handleAction(
            {
              id: postAction.id,
              type: typeof postAction.type === "string" && postAction.type ? postAction.type : "call_flow",
            },
            actionPayload,
            chooseButton
          );
        }
        status.textContent = "Upload complete.";
      } catch (error) {
        status.classList.add("is-error");
        status.textContent = error && error.message ? error.message : "Upload failed.";
      } finally {
        chooseButton.disabled = disabled;
        input.__n3UploadPickerPostAction = null;
        input.value = "";
      }
    };

    renderSelectedFiles();
    return wrapper;
  }

  function refreshUploadVisibility(scope) {
    const rootNode = scope && typeof scope.querySelectorAll === "function" ? scope : document;
    const uploads = rootNode.querySelectorAll(".ui-upload[data-upload-name]");
    uploads.forEach((uploadNode) => {
      const uploadName = uploadNode && uploadNode.dataset ? String(uploadNode.dataset.uploadName || "").trim() : "";
      const managed = _isComposerManagedUpload(uploadName);
      uploadNode.classList.toggle("ui-upload-hidden-surface", managed);
    });
  }

  root.renderUploadElement = renderUploadElement;
  root.refreshUploadVisibility = refreshUploadVisibility;
  root.openUploadInputPicker = _openUploadInputPicker;
  root.getUploadStateSnapshot = getUploadStateSnapshot;
  window.N3UIRender = root;
})();
