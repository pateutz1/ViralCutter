function editorMarkup() {
  return `
<section class="vc-card">
  <h3>${icon("captions")} Source</h3>
  <div class="vc-compact-grid">
    <div class="vc-field">
      <label for="editor-project">Project</label>
      <div class="vc-field-control">
        <select class="vc-select" id="editor-project"></select>
        <button type="button" class="vc-btn" id="editor-refresh">Refresh</button>
      </div>
    </div>
    <div class="vc-field">
      <label for="editor-file">Subtitle file</label>
      <div class="vc-field-control">
        <select class="vc-select" id="editor-file"></select>
        <button type="button" class="vc-btn vc-btn-primary vc-btn-generate" id="editor-load">${icon("folder")} Load</button>
      </div>
    </div>
  </div>
</section>
<section class="vc-card">
  <div class="vc-editor-head">
    <h3>${icon("segments")} Cues</h3>
    <span class="vc-editor-count" id="editor-count">0 cues</span>
  </div>
  <p class="vc-editor-empty" id="editor-empty">Load a subtitle file to edit timing and text.</p>
  <div class="vc-table-wrap" id="editor-table-wrap" hidden>
    <table class="vc-table" id="editor-table">
      <thead><tr><th class="col-time">Start</th><th class="col-time">End</th><th>Text</th><th class="col-act"></th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
  <div class="vc-actions" style="margin-top:12px">
    <button type="button" class="vc-btn vc-btn-generate" id="editor-add-row">${icon("plus")} Add cue</button>
  </div>
</section>
<section class="vc-card vc-generate" id="editor-render-card" data-state="idle">
  <h3>${icon("generate")} Render</h3>
  <div class="vc-generate-bar">
    <div class="vc-generate-meta">
      <span class="vc-generate-dot" aria-hidden="true"></span>
      <div>
        <strong id="editor-state">Ready</strong>
        <small id="editor-status">Select a project and file.</small>
      </div>
    </div>
    <div class="vc-generate-actions">
      <button type="button" class="vc-btn vc-btn-primary vc-btn-generate" id="editor-save">${icon("actions")} Save Changes</button>
      <button type="button" class="vc-btn vc-btn-generate" id="editor-render-one">Render This Segment</button>
      <button type="button" class="vc-btn vc-btn-generate" id="editor-render-all">Render All</button>
    </div>
  </div>
</section>`;
}

function editorRows() {
  return [...document.querySelectorAll("#editor-table tbody tr")].map((row) => {
    const inputs = row.querySelectorAll("input");
    return [inputs[0].value, inputs[1].value, inputs[2].value];
  });
}

function syncEditorEmpty() {
  const n = document.querySelectorAll("#editor-table tbody tr").length;
  const count = $("editor-count");
  const empty = $("editor-empty");
  const wrap = $("editor-table-wrap");
  if (count) count.textContent = n === 1 ? "1 cue" : `${n} cues`;
  if (empty) empty.hidden = n > 0;
  if (wrap) wrap.hidden = n === 0;
}

function setEditorState(state, title, detail) {
  const card = $("editor-render-card");
  if (card) card.dataset.state = state;
  const label = $("editor-state");
  const note = $("editor-status");
  if (label) label.textContent = title;
  if (note && detail != null) note.textContent = detail;
}

function setEditorBusy(busy) {
  ["editor-load", "editor-save", "editor-render-one", "editor-render-all", "editor-refresh", "editor-add-row"].forEach((id) => {
    const el = $(id);
    if (el) el.disabled = busy;
  });
}

function addEditorRow(start = "00:00:00,000", end = "00:00:00,000", text = "") {
  const tbody = document.querySelector("#editor-table tbody");
  const tr = document.createElement("tr");
  tr.innerHTML = `<td><input value="${start}" /></td><td><input value="${end}" /></td><td><input value="${String(text).replace(/"/g, "&quot;")}" /></td><td><button type="button" class="vc-editor-del editor-del" aria-label="Delete cue">×</button></td>`;
  tr.querySelector(".editor-del").addEventListener("click", () => {
    tr.remove();
    syncEditorEmpty();
  });
  tbody.appendChild(tr);
  syncEditorEmpty();
}

window.initEditor = function initEditor() {
  $("view-editor").innerHTML = editorMarkup();
  const projectEl = $("editor-project");
  const fileEl = $("editor-file");
  fillSelect(projectEl, VC.options.projects || [], VC.state.editor_project);
  syncEditorEmpty();

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
    setEditorBusy(true);
    setEditorState("running", "Loading", "Reading subtitle cues…");
    try {
      const out = await api(`/api/editor/load?project=${encodeURIComponent(projectEl.value)}&file=${encodeURIComponent(fileEl.value)}`);
      document.querySelector("#editor-table tbody").innerHTML = "";
      (out.rows || []).forEach((row) => addEditorRow(row[0], row[1], row[2]));
      $("editor-status").dataset.path = out.path;
      setEditorState("done", "Loaded", out.status);
    } catch (err) {
      setEditorState("error", "Failed", err.message);
    } finally {
      setEditorBusy(false);
    }
  });
  $("editor-save").addEventListener("click", async () => {
    setEditorBusy(true);
    setEditorState("running", "Saving", "Writing cue changes…");
    try {
      const out = await api("/api/editor/save", { method: "POST", body: JSON.stringify({ path: $("editor-status").dataset.path, rows: editorRows() }) });
      setEditorState("done", "Saved", out.status);
    } catch (err) {
      setEditorState("error", "Failed", err.message);
    } finally {
      setEditorBusy(false);
    }
  });
  $("editor-render-one").addEventListener("click", async () => {
    setEditorBusy(true);
    setEditorState("running", "Rendering", "Burning captions onto this segment…");
    try {
      const out = await api("/api/editor/render-one", { method: "POST", body: JSON.stringify({ path: $("editor-status").dataset.path, settings: formPayload() }) });
      setEditorState("done", "Rendered", out.status);
    } catch (err) {
      setEditorState("error", "Failed", err.message);
    } finally {
      setEditorBusy(false);
    }
  });
  $("editor-render-all").addEventListener("click", async () => {
    setEditorBusy(true);
    setEditorState("running", "Rendering", "Burning captions onto every clip…");
    try {
      const out = await api("/api/editor/render-all", { method: "POST", body: JSON.stringify({ project: projectEl.value, settings: formPayload() }) });
      setEditorState("done", "Rendered", out.status);
    } catch (err) {
      setEditorState("error", "Failed", err.message);
    } finally {
      setEditorBusy(false);
    }
  });
  if (projectEl.value) loadFiles().catch(() => {});
};
