function editorMarkup() {
  return `
<section class="vc-card">
  <h3>${icon("folder")} Project</h3>
  <div class="vc-row">
    <div class="vc-field"><label for="editor-project">Select Project</label><select class="vc-select" id="editor-project"></select></div>
    <button type="button" class="vc-btn" id="editor-refresh">Refresh</button>
  </div>
  <div class="vc-row">
    <div class="vc-field"><label for="editor-file">Select Subtitle File</label><select class="vc-select" id="editor-file"></select></div>
    <button type="button" class="vc-btn" id="editor-load">Load Subtitles</button>
  </div>
</section>
<section class="vc-card">
  <h3>${icon("segments")} Segments</h3>
  <div class="vc-table-wrap">
    <table class="vc-table" id="editor-table">
      <thead><tr><th class="col-time">Start</th><th class="col-time">End</th><th>Text</th><th class="col-act"></th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
  <div class="vc-actions" style="margin-top:12px">
    <button type="button" class="vc-btn" id="editor-add-row">Add row</button>
  </div>
</section>
<section class="vc-card">
  <h3>${icon("actions")} Actions</h3>
  <div class="vc-actions">
    <button type="button" class="vc-btn vc-btn-primary" id="editor-save">Save Changes</button>
    <button type="button" class="vc-btn" id="editor-render-one">Render This Segment</button>
    <button type="button" class="vc-btn vc-btn-stop" id="editor-render-all">Render All</button>
  </div>
  <p class="vc-status" id="editor-status">Select a project and file.</p>
</section>`;
}

function editorRows() {
  return [...document.querySelectorAll("#editor-table tbody tr")].map((row) => {
    const inputs = row.querySelectorAll("input");
    return [inputs[0].value, inputs[1].value, inputs[2].value];
  });
}

function addEditorRow(start = "00:00:00,000", end = "00:00:00,000", text = "") {
  const tbody = document.querySelector("#editor-table tbody");
  const tr = document.createElement("tr");
  tr.innerHTML = `<td><input value="${start}" /></td><td><input value="${end}" /></td><td><input value="${String(text).replace(/"/g, "&quot;")}" /></td><td><button type="button" class="vc-btn editor-del">×</button></td>`;
  tr.querySelector(".editor-del").addEventListener("click", () => tr.remove());
  tbody.appendChild(tr);
}

window.initEditor = function initEditor() {
  $("view-editor").innerHTML = editorMarkup();
  const projectEl = $("editor-project");
  const fileEl = $("editor-file");
  fillSelect(projectEl, VC.options.projects || [], VC.state.editor_project);

  async function loadFiles() {
    const out = await api(`/api/editor/files?project=${encodeURIComponent(projectEl.value || "")}`);
    fillSelect(fileEl, out.files || []);
  }
  projectEl.addEventListener("change", loadFiles);
  $("editor-refresh").addEventListener("click", async () => {
    const out = await api("/api/projects");
    fillSelect(projectEl, out.projects || [], projectEl.value);
    await loadFiles();
  });
  $("editor-add-row").addEventListener("click", () => addEditorRow());
  $("editor-load").addEventListener("click", async () => {
    const out = await api(`/api/editor/load?project=${encodeURIComponent(projectEl.value)}&file=${encodeURIComponent(fileEl.value)}`);
    document.querySelector("#editor-table tbody").innerHTML = "";
    (out.rows || []).forEach((row) => addEditorRow(row[0], row[1], row[2]));
    $("editor-status").textContent = out.status;
    $("editor-status").dataset.path = out.path;
  });
  $("editor-save").addEventListener("click", async () => {
    const out = await api("/api/editor/save", { method: "POST", body: JSON.stringify({ path: $("editor-status").dataset.path, rows: editorRows() }) });
    $("editor-status").textContent = out.status;
  });
  $("editor-render-one").addEventListener("click", async () => {
    const out = await api("/api/editor/render-one", { method: "POST", body: JSON.stringify({ path: $("editor-status").dataset.path, settings: formPayload() }) });
    $("editor-status").textContent = out.status;
  });
  $("editor-render-all").addEventListener("click", async () => {
    const out = await api("/api/editor/render-all", { method: "POST", body: JSON.stringify({ project: projectEl.value, settings: formPayload() }) });
    $("editor-status").textContent = out.status;
  });
  if (projectEl.value) loadFiles().catch(() => {});
};
