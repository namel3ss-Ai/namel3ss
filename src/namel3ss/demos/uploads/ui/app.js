const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const dropZone = document.getElementById("dropZone");
const fileMeta = document.getElementById("fileMeta");
const statusEl = document.getElementById("status");
const uploadList = document.getElementById("uploadList");
const traceList = document.getElementById("traceList");
const refreshBtn = document.getElementById("refreshBtn");

let selectedFile = null;

function setStatus(message, tone = "info") {
  statusEl.textContent = message;
  statusEl.dataset.tone = tone;
}

function renderUploads(items) {
  uploadList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No uploads yet.";
    uploadList.appendChild(empty);
    return;
  }
  items.forEach((upload) => {
    const item = document.createElement("div");
    item.className = "list-item";

    const title = document.createElement("h3");
    title.textContent = upload.name || "upload";

    const meta = document.createElement("div");
    meta.className = "meta";
    addMetaRow(meta, "Content type", upload.content_type || "unknown");
    addMetaRow(meta, "Bytes", upload.bytes == null ? "" : String(upload.bytes));
    addMetaRow(meta, "Checksum", upload.checksum || "");
    addMetaRow(meta, "Stored path", upload.stored_path || "");

    item.appendChild(title);
    item.appendChild(meta);
    uploadList.appendChild(item);
  });
}

function renderTraces(traces) {
  traceList.innerHTML = "";
  if (!traces.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No upload events recorded yet.";
    traceList.appendChild(empty);
    return;
  }
  traces.forEach((trace) => {
    const item = document.createElement("div");
    item.className = "trace-item";
    const title = document.createElement("strong");
    title.textContent = trace.title || trace.type || "event";
    const meta = document.createElement("div");
    meta.className = "meta";
    addMetaRow(meta, "Name", trace.name || "");
    addMetaRow(meta, "Bytes", trace.bytes == null ? "" : String(trace.bytes));
    addMetaRow(meta, "Checksum", trace.checksum || "");
    addMetaRow(meta, "Stored path", trace.stored_path || "");
    item.appendChild(title);
    item.appendChild(meta);
    traceList.appendChild(item);
  });
}

async function fetchUploads() {
  try {
    const response = await fetch("/api/uploads");
    const data = await response.json();
    if (!data.ok) {
      throw new Error(data.message || "Unable to load uploads");
    }
    renderUploads(Array.isArray(data.uploads) ? data.uploads : []);
  } catch (err) {
    setStatus(String(err), "error");
  }
}

function modeValue() {
  const selected = document.querySelector("input[name=mode]:checked");
  return selected ? selected.value : "multipart";
}

async function sendUpload(file, mode) {
  const name = file.name || "upload";
  const url = `/api/upload?name=${encodeURIComponent(name)}`;
  if (mode === "stream") {
    const headers = {
      "Content-Type": file.type || "application/octet-stream",
      "X-Upload-Name": name,
    };
    if (file.stream) {
      return fetch(url, {
        method: "POST",
        headers,
        body: file.stream(),
        duplex: "half",
      });
    }
    const buffer = await file.arrayBuffer();
    return fetch(url, {
      method: "POST",
      headers,
      body: buffer,
    });
  }
  const form = new FormData();
  form.append("file", file, name);
  return fetch(url, {
    method: "POST",
    body: form,
  });
}

function attachDropZone() {
  dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("is-drag");
  });
  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("is-drag");
  });
  dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-drag");
    const file = event.dataTransfer.files[0];
    if (file) {
      selectedFile = file;
      fileMeta.textContent = `${file.name} (${file.size} bytes)`;
    }
  });
}

fileInput.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) {
    selectedFile = file;
    fileMeta.textContent = `${file.name} (${file.size} bytes)`;
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedFile) {
    setStatus("Choose a file before uploading.", "error");
    return;
  }
  setStatus("Uploading...", "pending");
  try {
    const response = await sendUpload(selectedFile, modeValue());
    const data = await response.json();
    if (!data.ok) {
      throw new Error(data.message || "Upload failed");
    }
    setStatus("Upload stored.", "success");
    renderTraces(Array.isArray(data.traces) ? data.traces : []);
    await fetchUploads();
  } catch (err) {
    setStatus(String(err), "error");
  }
});

refreshBtn.addEventListener("click", () => {
  fetchUploads();
});

attachDropZone();
fetchUploads();
renderTraces([]);

function addMetaRow(container, label, value) {
  const row = document.createElement("div");
  const text = document.createTextNode(`${label}: `);
  const span = document.createElement("span");
  span.textContent = value;
  row.appendChild(text);
  row.appendChild(span);
  container.appendChild(row);
}
