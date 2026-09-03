function settingsMarkup() {
  return `
<form id="settings-form">
  <section class="vc-card">
    <h3>${icon("api")} API</h3>
    <div class="vc-api-section">
      <div class="vc-api-section-title"><span>01</span><strong>Provider & credentials</strong></div>
      <div class="vc-row">
        <div class="vc-field">
          <label for="ai_backend">AI Backend</label>
          <select class="vc-select" id="ai_backend" name="ai_backend">
            <option value="gemini">Gemini</option>
            <option value="groq">Groq</option>
            <option value="cloudflare">Cloudflare</option>
            <option value="g4f">G4F</option>
            <option value="manual">Manual</option>
          </select>
        </div>
        <div class="vc-field" id="field-api-key">
          <label for="api_key">Gemini API Key</label>
          <input class="vc-input" id="api_key" name="api_key" type="password" autocomplete="off" />
        </div>
      </div>
    </div>
    <div class="vc-api-section">
      <div class="vc-api-section-title"><span>02</span><strong>Model configuration</strong></div>
      <div class="vc-row">
        <div class="vc-field" id="field-ai-model">
          <label for="ai_model_name">AI Model</label>
          <select class="vc-select" id="ai_model_name" name="ai_model_name"></select>
        </div>
        <div class="vc-field vc-field-chunk">
          <label for="chunk_size">Chunk Size</label>
          <input class="vc-input" id="chunk_size" name="chunk_size" type="number" data-num="1" />
        </div>
      </div>
    </div>
  </section>
  <section class="vc-card">
    <h3>${icon("sliders")} Logs</h3>
    <p class="vc-help">Log verbosity and export options will land here later.</p>
  </section>
</form>`;
}

window.initSettings = function initSettings() {
  $("view-settings").innerHTML = settingsMarkup();
  const state = VC.state;
  const models = (VC.options.models || {})[state.ai_backend || "gemini"] || [];
  fillSelect($("ai_model_name"), models, state.ai_model_name);
  applyFields({
    ai_backend: state.ai_backend,
    ai_model_name: state.ai_model_name,
    chunk_size: state.chunk_size,
  });
  setField($("api_key"), VC.apiKey);

  $("settings-form").addEventListener("change", async (event) => {
    if (event.target.name === "ai_backend") {
      const info = await api(`/api/backend/${event.target.value}`);
      fillSelect($("ai_model_name"), info.models, info.model);
      $("chunk_size").value = info.chunk_size;
      $("field-api-key").hidden = !info.show_api_key;
      $("api_key").value = info.api_key || "";
      document.querySelector("label[for=api_key]").textContent = info.api_label;
    }
    scheduleSave(formPayload());
  });
};
