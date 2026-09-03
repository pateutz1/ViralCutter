function createMarkup() {
  return `
<form id="create-form">
  <div class="vc-grid vc-grid-2">
    <section class="vc-card">
      <h3>${icon("video")} Video</h3>
      <div class="vc-field">
        <span class="vc-label">Input Source</span>
        <div class="vc-source">
          <label><input type="radio" name="input_source" value="YouTube URL" /> YouTube URL</label>
          <label><input type="radio" name="input_source" value="Existing Project" /> Existing Project</label>
          <label><input type="radio" name="input_source" value="Upload Video" /> Upload Video</label>
        </div>
      </div>
      <div class="vc-field" id="field-url">
        <label for="url">YouTube URL</label>
        <input class="vc-input" id="url" name="url" placeholder="https://www.youtube.com/watch?v=..." />
      </div>
      <div class="vc-field" id="field-project" hidden>
        <label for="project_name">Select Project</label>
        <select class="vc-select" id="project_name" name="project_name"></select>
      </div>
      <div class="vc-field" id="field-upload" hidden>
        <label for="video_file">Upload Video</label>
        <input class="vc-input" id="video_file" type="file" accept="video/*" />
      </div>
      <div class="vc-options-row" id="video-options">
        <div class="vc-field">
          <label for="video_quality">Video Quality</label>
          <select class="vc-select" id="video_quality" name="video_quality">
            <option value="best">Best Quality</option>
            <option value="1080p">1080p</option>
            <option value="720p">720p</option>
            <option value="480p">480p</option>
          </select>
        </div>
        <div class="vc-field">
          <label class="vc-check"><input type="checkbox" id="use_youtube_subs" name="use_youtube_subs" /> <strong>Use YouTube Subs</strong></label>
          <span class="vc-subs-hint">Download and use official subtitles if available. (Recommended, it speeds up the process)</span>
        </div>
      </div>
    </section>

    <section class="vc-card vc-card-cutting">
      <h3>${icon("cutting")} Cutting</h3>
      <div class="vc-field vc-field-md">
        <label for="generation_profile">Generation Profile</label>
        <select class="vc-select" id="generation_profile" name="generation_profile"></select>
        <p class="vc-help">Sets clip count, duration, face mode, tracking speed, and face preset together.</p>
      </div>
      <div class="vc-compact-row">
        <div class="vc-field vc-field-sm">
          <label for="segments">Segments</label>
          <input class="vc-input" id="segments" name="segments" type="number" data-num="1" />
        </div>
        <label class="vc-check vc-check-inline"><input type="checkbox" id="viral" name="viral" /> <strong>Viral Mode</strong></label>
      </div>
      <div class="vc-field vc-field-md" id="field-themes">
        <label for="themes">Themes</label>
        <input class="vc-input" id="themes" name="themes" placeholder="funny, sad..." />
      </div>
      <div class="vc-compact-row">
        <div class="vc-field vc-field-sm"><label for="min_duration">Min Duration (s)</label><input class="vc-input" id="min_duration" name="min_duration" type="number" data-num="1" /></div>
        <div class="vc-field vc-field-sm"><label for="max_duration">Max Duration (s)</label><input class="vc-input" id="max_duration" name="max_duration" type="number" data-num="1" /></div>
      </div>
      <label class="vc-check"><input type="checkbox" id="text_safe_selection" name="text_safe_selection" /> <strong>Text Safe Selection</strong></label>
      <div class="vc-field vc-field-md">
        <label for="max_text_frame_percent">Crop-Risk Text Max (%)</label>
        <input class="vc-input" id="max_text_frame_percent" name="max_text_frame_percent" type="range" min="0" max="100" step="1" />
      </div>
    </section>
  </div>

  <div class="vc-section-divider"><span>02</span><div><strong>Processing</strong><small>Choose how clips are detected, framed, and transcribed.</small></div></div>
  <div class="vc-grid vc-grid-2">
    <section class="vc-card">
      <h3>${icon("face")} Face / Vertical</h3>
      <div class="vc-row">
        <div class="vc-field"><label for="workflow">Workflow</label>
          <select class="vc-select" id="workflow" name="workflow">
            <option>Full</option><option>Cut Only</option><option>Subtitles Only</option>
          </select>
        </div>
        <div class="vc-field"><label for="face_model">Face Model</label>
          <select class="vc-select" id="face_model" name="face_model"><option>insightface</option><option>mediapipe</option></select>
        </div>
      </div>
      <div class="vc-row">
        <div class="vc-field"><label for="face_mode">Face Mode</label>
          <select class="vc-select" id="face_mode" name="face_mode">
            <option value="auto">Auto</option><option value="1">1</option><option value="2">2</option>
            <option value="fixed_center">Fixed Center (No Tracking)</option>
          </select>
        </div>
        <div class="vc-field"><label for="no_face_mode">No Face Fallback</label>
          <select class="vc-select" id="no_face_mode" name="no_face_mode">
            <option value="padding">Padding (9:16)</option><option value="zoom">Zoom (Center)</option>
          </select>
        </div>
      </div>
      <div class="vc-field">
        <label for="face_detect_interval">Face Det. Interval</label>
        <input class="vc-input" id="face_detect_interval" name="face_detect_interval" />
      </div>
      <details class="vc-nested">
        <summary>${icon("sliders")} Advanced Face Settings</summary>
        <div class="vc-field"><label for="face_preset">Configuration Presets</label><select class="vc-select" id="face_preset" name="face_preset"></select></div>
        <div class="vc-slider-grid">
          <div class="vc-field"><label for="face_filter_thresh">Ignore Small Faces</label><input class="vc-input" id="face_filter_thresh" name="face_filter_thresh" type="number" step="0.05" min="0" max="1" data-num="1" /><p class="vc-help">Relative size to ignore background.</p></div>
          <div class="vc-field"><label for="face_two_thresh">Threshold for 2 Faces</label><input class="vc-input" id="face_two_thresh" name="face_two_thresh" type="number" step="0.05" min="0" max="1" data-num="1" /></div>
          <div class="vc-field"><label for="face_conf_thresh">Minimum Confidence</label><input class="vc-input" id="face_conf_thresh" name="face_conf_thresh" type="number" step="0.05" min="0" max="1" data-num="1" /></div>
          <div class="vc-field"><label for="face_dead_zone">Dead Zone</label><input class="vc-input" id="face_dead_zone" name="face_dead_zone" type="number" step="5" min="0" max="120" data-num="1" /></div>
        </div>
        <details>
          <summary>Experimental: Active Speaker & Motion</summary>
          <div class="vc-field"><label for="experimental_preset">Configuration Presets</label><select class="vc-select" id="experimental_preset" name="experimental_preset"></select></div>
          <label class="vc-check"><input type="checkbox" id="focus_active_speaker" name="focus_active_speaker" /> <strong>Focus on Speaker</strong></label>
          <div class="vc-slider-grid">
            <div class="vc-field"><label for="active_speaker_mar">MAR Threshold</label><input class="vc-input" id="active_speaker_mar" name="active_speaker_mar" type="number" step="0.005" min="0.01" max="0.20" data-num="1" /></div>
            <div class="vc-field"><label for="active_speaker_score_diff">Score Difference</label><input class="vc-input" id="active_speaker_score_diff" name="active_speaker_score_diff" type="number" step="0.5" min="0.5" max="10" data-num="1" /></div>
            <label class="vc-check"><input type="checkbox" id="include_motion" name="include_motion" /> <strong>Consider Motion</strong></label>
            <div class="vc-field"><label for="active_speaker_motion_threshold">Motion Dead Zone</label><input class="vc-input" id="active_speaker_motion_threshold" name="active_speaker_motion_threshold" type="number" step="0.5" min="0" max="20" data-num="1" /></div>
            <div class="vc-field"><label for="active_speaker_motion_sensitivity">Motion Sensitivity</label><input class="vc-input" id="active_speaker_motion_sensitivity" name="active_speaker_motion_sensitivity" type="number" step="0.01" min="0.01" max="0.5" data-num="1" /></div>
            <div class="vc-field"><label for="active_speaker_decay">Switch Speed</label><input class="vc-input" id="active_speaker_decay" name="active_speaker_decay" type="number" step="0.5" min="0.5" max="5" data-num="1" /></div>
          </div>
        </details>
      </details>
    </section>

    <section class="vc-card">
      <h3>${icon("captions")} Captions</h3>
      <div class="vc-row">
        <div class="vc-field">
          <label for="whisper_backend">Whisper Backend</label>
          <select class="vc-select" id="whisper_backend" name="whisper_backend"></select>
        </div>
        <label class="vc-check vc-check-inline"><input type="checkbox" id="enable_captions" name="enable_captions" /> <strong>Enable Captions</strong></label>
      </div>
      <div class="vc-field vc-field-md">
        <label for="translate_target">Translate Subtitles To</label>
        <select class="vc-select" id="translate_target" name="translate_target">
          <option>None</option><option>pt</option><option>en</option><option>es</option><option>fr</option>
          <option>de</option><option>it</option><option>ru</option><option>ja</option><option>ko</option><option>zh-CN</option>
        </select>
      </div>
      <details class="vc-nested">
        <summary>${icon("subtitles")} Subtitle Settings (alpha)</summary>
        <div class="vc-row">
          <div class="vc-field"><label for="subtitle_preset">Quick Presets</label><select class="vc-select" id="subtitle_preset" name="subtitle_preset"></select></div>
          <label class="vc-check vc-check-inline"><input type="checkbox" id="use_custom_subs" name="use_custom_subs" /> <strong>Enable Subtitle Customization</strong></label>
        </div>
        <div id="subtitle-preview"></div>
        <div class="vc-actions" style="margin:10px 0 16px">
          <button type="button" class="vc-btn" id="preview-video-btn">Render Animated Preview</button>
        </div>
        <video id="subtitle-preview-video" controls hidden style="width:min(240px,100%);border-radius:12px"></video>
        <details>
          <summary>Advanced Settings</summary>
          <div class="vc-row">
            <div class="vc-field"><label for="font_name">Font Name</label><input class="vc-input" id="font_name" name="font_name" /></div>
            <div class="vc-field"><label for="font_size">Font Size</label><input class="vc-input" id="font_size" name="font_size" type="number" min="8" max="80" data-num="1" /></div>
            <div class="vc-field"><label for="highlight_size">Highlight Size</label><input class="vc-input" id="highlight_size" name="highlight_size" type="number" min="8" max="80" data-num="1" /></div>
          </div>
          <div class="vc-row">
            <div class="vc-field"><label for="font_color">Base Color</label><input class="vc-input" id="font_color" name="font_color" type="color" /></div>
            <div class="vc-field"><label for="highlight_color">Highlight Color</label><input class="vc-input" id="highlight_color" name="highlight_color" type="color" /></div>
            <div class="vc-field"><label for="outline_color">Outline Color</label><input class="vc-input" id="outline_color" name="outline_color" type="color" /></div>
            <div class="vc-field"><label for="shadow_color">Shadow Color</label><input class="vc-input" id="shadow_color" name="shadow_color" type="color" /></div>
          </div>
          <div class="vc-row">
            <div class="vc-field"><label for="outline_thickness">Outline Thickness</label><input class="vc-input" id="outline_thickness" name="outline_thickness" type="number" step="0.5" min="0" max="10" data-num="1" /></div>
            <div class="vc-field"><label for="shadow_size">Shadow Size</label><input class="vc-input" id="shadow_size" name="shadow_size" type="number" min="0" max="10" data-num="1" /></div>
            <div class="vc-field"><label for="border_s">Border Style</label>
              <select class="vc-select" id="border_s" name="border_s"><option value="1">Outline</option><option value="3">Opaque Box</option></select>
            </div>
          </div>
          <div class="vc-row">
            <label class="vc-check"><input type="checkbox" id="is_bold" name="is_bold" /> <strong>Bold</strong></label>
            <label class="vc-check"><input type="checkbox" id="is_italic" name="is_italic" /> <strong>Italic</strong></label>
            <label class="vc-check"><input type="checkbox" id="is_uppercase" name="is_uppercase" /> <strong>Uppercase</strong></label>
            <label class="vc-check"><input type="checkbox" id="remove_punc" name="remove_punc" /> <strong>Remove Punctuation</strong></label>
            <label class="vc-check"><input type="checkbox" id="under" name="under" /> <strong>Underline</strong></label>
            <label class="vc-check"><input type="checkbox" id="strike" name="strike" /> <strong>Strikeout</strong></label>
          </div>
          <div class="vc-row">
            <div class="vc-field"><label for="vertical_pos">V-Pos</label><input class="vc-input" id="vertical_pos" name="vertical_pos" type="number" min="0" max="500" data-num="1" /></div>
            <div class="vc-field"><label for="alignment">Alignment</label>
              <select class="vc-select" id="alignment" name="alignment"><option value="1">Left</option><option value="2">Center</option><option value="3">Right</option></select>
            </div>
            <div class="vc-field"><label for="gap">Gap Limit</label><input class="vc-input" id="gap" name="gap" type="number" step="0.1" min="0" max="5" data-num="1" /></div>
            <div class="vc-field"><label for="mode">Mode</label>
              <select class="vc-select" id="mode" name="mode"><option value="highlight">Highlight</option><option value="word_by_word">Word by Word</option><option value="no_highlight">No Highlight</option></select>
            </div>
            <div class="vc-field"><label for="w_block">Words per Block</label><input class="vc-input" id="w_block" name="w_block" type="number" min="1" max="20" data-num="1" /></div>
          </div>
        </details>
      </details>
    </section>
  </div>
<div class="vc-section-divider"><span>03</span><div><strong>Output</strong><small>Start processing and follow the render in real time.</small></div></div>
  <section class="vc-card">
    <h3>${icon("generate")} Generate</h3>
    <div class="vc-actions">
      <button type="button" class="vc-btn vc-btn-primary" id="start-btn">Start Processing</button>
      <button type="button" class="vc-btn vc-btn-stop" id="stop-btn" hidden>Stop</button>
    </div>
    <div class="vc-field" style="margin-top:14px">
      <label for="logs">Logs</label>
      <textarea class="vc-textarea" id="logs" readonly></textarea>
    </div>
    <div id="results"></div>
  </section>
</form>`;
}

function applyFields(data) {
  Object.entries(data || {}).forEach(([key, value]) => {
    const el = document.querySelector(`#create-form [name="${key}"], #settings-form [name="${key}"]`);
    setField(el, value);
    if (el && el.type === "radio") {
      const radio = document.querySelector(`#create-form [name="${key}"][value="${value}"]`);
      if (radio) radio.checked = true;
    }
  });
}

function syncSource() {
  const source = document.querySelector("#create-form [name=input_source]:checked")?.value || "YouTube URL";
  $("field-url").hidden = source !== "YouTube URL";
  $("field-project").hidden = source !== "Existing Project";
  $("field-upload").hidden = source !== "Upload Video";
  $("video-options").hidden = false;
  if (source === "Existing Project" && $("workflow").value === "Full") $("workflow").value = "Subtitles Only";
  if (source !== "Existing Project" && $("workflow").value === "Subtitles Only") $("workflow").value = "Full";
}

function formPayload() {
  const data = {
    ...collectNamed($("create-form") || document.createElement("form")),
    ...collectNamed($("settings-form") || document.createElement("form")),
  };
  const source = document.querySelector("#create-form [name=input_source]:checked")?.value;
  data.input_source = source;
  data.video_file = window.VC_UPLOAD_PATH || "";
  data.border_s = Number(data.border_s);
  data.alignment = Number(data.alignment);
  return data;
}

async function refreshPreview() {
  const out = await api("/api/subtitles/preview", { method: "POST", body: JSON.stringify({ data: formPayload() }) });
  $("subtitle-preview").innerHTML = out.html || "";
}

window.initCreate = function initCreate() {
  $("view-create").innerHTML = createMarkup();
  const state = VC.state;
  fillSelect($("project_name"), VC.options.projects || [], state.editor_project);
  fillSelect($("generation_profile"), VC.options.generation_profiles || [], state.generation_profile);
  fillSelect($("face_preset"), VC.options.face_presets || [], state.face_preset);
  fillSelect($("experimental_preset"), VC.options.experimental_presets || [], state.experimental_preset);
  fillSelect($("subtitle_preset"), VC.options.subtitle_presets || [], state.subtitle_preset);
  fillSelect($("whisper_backend"), VC.options.whisper_backends || [], state.whisper_backend);
  applyFields(state);
  const sourceRadio = document.querySelector(`#create-form [name=input_source][value="${state.input_source || "YouTube URL"}"]`);
  if (sourceRadio) sourceRadio.checked = true;
  $("field-themes").hidden = Boolean(state.viral);
  syncSource();
  refreshPreview().catch(() => {});

  $("create-form").addEventListener("change", async (event) => {
    const name = event.target.name;
    if (name === "input_source") syncSource();
    if (name === "viral") $("field-themes").hidden = $("viral").checked;
    if (name === "generation_profile") applyFields(await api("/api/presets/generation", { method: "POST", body: JSON.stringify({ name: event.target.value }) }));
    if (name === "face_preset") applyFields(await api("/api/presets/face", { method: "POST", body: JSON.stringify({ name: event.target.value }) }));
    if (name === "experimental_preset") applyFields(await api("/api/presets/experimental", { method: "POST", body: JSON.stringify({ name: event.target.value }) }));
    if (name === "subtitle_preset") {
      const mapped = await api("/api/subtitles/preset", { method: "POST", body: JSON.stringify({ name: event.target.value }) });
      applyFields(mapped);
    }
    scheduleSave(formPayload());
    refreshPreview().catch(() => {});
  });

  $("video_file").addEventListener("change", async () => {
    const file = $("video_file").files[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    const res = await fetch("/api/upload", { method: "POST", body });
    const data = await res.json();
    window.VC_UPLOAD_PATH = data.path;
  });

  $("preview-video-btn").addEventListener("click", async () => {
    $("preview-video-btn").disabled = true;
    try {
      const out = await api("/api/subtitles/preview-video", { method: "POST", body: JSON.stringify({ data: formPayload() }) });
      const video = $("subtitle-preview-video");
      video.src = out.url;
      video.hidden = false;
      video.play().catch(() => {});
    } finally {
      $("preview-video-btn").disabled = false;
    }
  });

  $("start-btn").addEventListener("click", startJob);
  $("stop-btn").addEventListener("click", () => api("/api/run/stop", { method: "POST" }));
};

async function startJob() {
  const startBtn = $("start-btn");
  const stopBtn = $("stop-btn");
  const logs = $("logs");
  startBtn.disabled = true;
  startBtn.textContent = "Running...";
  stopBtn.hidden = false;
  logs.value = "";
  $("results").innerHTML = "";
  try {
    const { job_id } = await api("/api/run", { method: "POST", body: JSON.stringify({ settings: formPayload() }) });
    const source = new EventSource(`/api/run/${job_id}/stream`);
    let sticky = true;
    logs.addEventListener("scroll", () => {
      sticky = logs.scrollHeight - logs.scrollTop - logs.clientHeight <= 50;
    });
    source.onmessage = (event) => {
      const data = JSON.parse(event.data);
      logs.value = data.logs || "";
      if (sticky) logs.scrollTop = logs.scrollHeight;
      if (data.done) {
        source.close();
        startBtn.disabled = false;
        startBtn.textContent = "Start Processing";
        stopBtn.hidden = true;
        $("results").innerHTML = data.gallery_html || "";
      }
    };
    source.onerror = () => {
      source.close();
      startBtn.disabled = false;
      startBtn.textContent = "Start Processing";
      stopBtn.hidden = true;
    };
  } catch (err) {
    logs.value = err.message;
    startBtn.disabled = false;
    startBtn.textContent = "Start Processing";
    stopBtn.hidden = true;
  }
}
