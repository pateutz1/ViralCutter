function libraryMarkup() {
  return `
<section class="vc-card">
  <h3>${icon("folder")} Projects</h3>
  <div class="vc-row">
    <div class="vc-field"><label for="library-project">Select Project</label><select class="vc-select" id="library-project"></select></div>
    <button type="button" class="vc-btn" id="library-refresh">Refresh List</button>
  </div>
</section>
<section class="vc-card">
  <h3>${icon("gallery")} Gallery</h3>
  <div id="library-gallery"></div>
</section>`;
}

async function loadGallery(project) {
  if (!project) {
    $("library-gallery").innerHTML = "<p class='vc-help'>No project selected.</p>";
    return;
  }
  const out = await api(`/api/library/gallery/${encodeURIComponent(project)}`);
  $("library-gallery").innerHTML = out.html || "";
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
