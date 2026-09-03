function libraryMarkup() {
  return `
<section class="vc-card">
  <h3>${icon("folder")} Source</h3>
  <div class="vc-field">
    <label for="library-project">Project</label>
    <div class="vc-field-control">
      <select class="vc-select" id="library-project"></select>
      <button type="button" class="vc-btn" id="library-refresh">Refresh</button>
    </div>
  </div>
</section>
<section class="vc-card">
  <div class="vc-editor-head">
    <h3>${icon("gallery")} Clips</h3>
    <span class="vc-editor-count" id="library-count">0 clips</span>
  </div>
  <p class="vc-editor-empty" id="library-empty">Select a project to browse finished shorts.</p>
  <div id="library-gallery"></div>
</section>`;
}

function syncLibraryGallery(html) {
  const gallery = $("library-gallery");
  const empty = $("library-empty");
  const count = $("library-count");
  gallery.innerHTML = html || "";
  const n = gallery.querySelectorAll(".vc-gallery-card").length;
  if (n === 0) gallery.innerHTML = "";
  if (count) count.textContent = n === 1 ? "1 clip" : `${n} clips`;
  if (empty) empty.hidden = n > 0;
}

async function loadGallery(project) {
  if (!project) {
    syncLibraryGallery("");
    $("library-empty").textContent = "Select a project to browse finished shorts.";
    return;
  }
  $("library-empty").hidden = false;
  $("library-empty").textContent = "Loading clips…";
  try {
    const out = await api(`/api/library/gallery/${encodeURIComponent(project)}`);
    syncLibraryGallery(out.html || "");
    if (!$("library-gallery").querySelector(".vc-gallery-card")) {
      $("library-empty").hidden = false;
      $("library-empty").textContent = "No clips found in this project.";
    }
  } catch (err) {
    syncLibraryGallery("");
    $("library-empty").hidden = false;
    $("library-empty").textContent = err.message;
  }
}

window.initLibrary = function initLibrary() {
  $("view-library").innerHTML = libraryMarkup();
  const select = $("library-project");
  fillSelect(select, VC.options.projects || [], VC.state.library_project);
  select.addEventListener("change", () => loadGallery(select.value));
  $("library-refresh").addEventListener("click", async () => {
    const out = await api("/api/projects");
    fillSelect(select, out.projects || [], select.value);
    await loadGallery(select.value);
  });
  if (select.value) loadGallery(select.value).catch(() => {});
};
