function updateTraceCopyButtons() {
  const outputBtn = document.getElementById("traceCopyOutput");
  const jsonBtn = document.getElementById("traceCopyJson");
  const has = !!selectedTrace;
  [outputBtn, jsonBtn].forEach((btn) => {
    if (!btn) return;
    btn.disabled = !has;
  });
  if (outputBtn) {
    outputBtn.onclick = () => {
      if (selectedTrace) copyText(selectedTrace.output ?? selectedTrace.result ?? "");
    };
  }
  if (jsonBtn) {
    jsonBtn.onclick = () => {
      if (selectedTrace) copyText(selectedTrace);
    };
  }
}
