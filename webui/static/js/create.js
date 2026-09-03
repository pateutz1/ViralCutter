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
          <span class="vc-label">Subtitles</span>
          <label class="vc-choice">
            <input type="checkbox" id="use_youtube_subs" name="use_youtube_subs" />
            <span class="vc-switch-track"></span>
            <span class="vc-choice-copy">
              <strong>Use YouTube Subs</strong>
              <small>Download and use official subtitles if available. (Recommended, it speeds up the process)</small>
            </span>
          </label>
        </div>
      </div>
    </section>

    <section class="vc-card vc-card-cutting">
      <h3>${icon("cutting")} Cutting</h3>
      <div class="vc-field vc-field-md">
        <label for="generation_profile">Generation Profile</label>
        <div class="vc-field-control">
          <select class="vc-select" id="generation_profile" name="generation_profile"></select>
          <label class="vc-switch"><input type="checkbox" id="viral" name="viral" /><span class="vc-switch-track"></span><span>Viral Mode</span></label>
        </div>
        <p class="vc-help">Sets clip count, duration, face mode, tracking speed, and face preset together.</p>
      </div>
      <div class="vc-field vc-field-md" id="field-themes">
        <label for="themes">Themes</label>
        <input class="vc-input" id="themes" name="themes" placeholder="funny, sad..." />
      </div>
      <div class="vc-compact-row">
        <div class="vc-field vc-field-sm"><label for="segments">Segments</label><input class="vc-input" id="segments" name="segments" type="number" data-num="1" /></div>
        <div class="vc-field vc-field-sm"><label for="min_duration">Min Duration (s)</label><input class="vc-input" id="min_duration" name="min_duration" type="number" data-num="1" /></div>
        <div class="vc-field vc-field-sm"><label for="max_duration">Max Duration (s)</label><input class="vc-input" id="max_duration" name="max_duration" type="number" data-num="1" /></div>
      </div>
      <label class="vc-switch vc-switch-block"><input type="checkbox" id="text_safe_selection" name="text_safe_selection" /><span class="vc-switch-track"></span><span>Text Safe Selection</span></label>
      <div class="vc-slider" data-default="15">
        <div class="vc-slider-head">
          <label for="max_text_frame_percent">Crop-Risk Text Max (%)</label>
          <div class="vc-slider-tools">
            <input class="vc-slider-num" id="max_text_frame_percent_num" type="number" min="0" max="100" step="1" />
            <button type="button" class="vc-slider-reset" id="crop-risk-reset" title="Reset" aria-label="Reset">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12a9 9 0 0 1 15.5-6.4M21 4v6h-6M21 12a9 9 0 0 1-15.5 6.4M3 20v-6h6"/></svg>
            </button>
          </div>
        </div>
        <input id="max_text_frame_percent" name="max_text_frame_percent" type="range" min="0" max="100" step="1" data-num="1" />
        <div class="vc-slider-scale"><span>0</span><span>100</span></div>
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
        <div class="vc-field">
          <label for="face_preset">Configuration Presets</label>
          <select class="vc-select" id="face_preset" name="face_preset"></select>
        </div>
        <div class="vc-compact-grid">
          <div class="vc-field"><label for="face_filter_thresh">Ignore Small Faces</label><input class="vc-input" id="face_filter_thresh" name="face_filter_thresh" type="number" step="0.05" min="0" max="1" data-num="1" title="Relative size to ignore background." /></div>
          <div class="vc-field"><label for="face_two_thresh">Threshold for 2 Faces</label><input class="vc-input" id="face_two_thresh" name="face_two_thresh" type="number" step="0.05" min="0" max="1" data-num="1" /></div>
          <div class="vc-field"><label for="face_conf_thresh">Minimum Confidence</label><input class="vc-input" id="face_conf_thresh" name="face_conf_thresh" type="number" step="0.05" min="0" max="1" data-num="1" /></div>
          <div class="vc-field"><label for="face_dead_zone">Dead Zone</label><input class="vc-input" id="face_dead_zone" name="face_dead_zone" type="number" step="5" min="0" max="120" data-num="1" /></div>
        </div>
        <details class="vc-nested vc-nested-sub">
          <summary>Experimental: Active Speaker & Motion</summary>
          <div class="vc-field">
            <label for="experimental_preset">Configuration Presets</label>
            <select class="vc-select" id="experimental_preset" name="experimental_preset"></select>
          </div>
          <div class="vc-compact-row" style="margin-bottom:10px">
            <label class="vc-switch"><input type="checkbox" id="focus_active_speaker" name="focus_active_speaker" /><span class="vc-switch-track"></span><span>Focus on Speaker</span></label>
            <label class="vc-switch"><input type="checkbox" id="include_motion" name="include_motion" /><span class="vc-switch-track"></span><span>Consider Motion</span></label>
          </div>
          <div class="vc-compact-grid">
            <div class="vc-field"><label for="active_speaker_mar">MAR Threshold</label><input class="vc-input" id="active_speaker_mar" name="active_speaker_mar" type="number" step="0.005" min="0.01" max="0.20" data-num="1" /></div>
            <div class="vc-field"><label for="active_speaker_score_diff">Score Difference</label><input class="vc-input" id="active_speaker_score_diff" name="active_speaker_score_diff" type="number" step="0.5" min="0.5" max="10" data-num="1" /></div>
            <div class="vc-field"><label for="active_speaker_motion_threshold">Motion Dead Zone</label><input class="vc-input" id="active_speaker_motion_threshold" name="active_speaker_motion_threshold" type="number" step="0.5" min="0" max="20" data-num="1" /></div>
            <div class="vc-field"><label for="active_speaker_motion_sensitivity">Motion Sensitivity</label><input class="vc-input" id="active_speaker_motion_sensitivity" name="active_speaker_motion_sensitivity" type="number" step="0.01" min="0.01" max="0.5" data-num="1" /></div>
            <div class="vc-field"><label for="active_speaker_decay">Switch Speed</label><input class="vc-input" id="active_speaker_decay" name="active_speaker_decay" type="number" step="0.5" min="0.5" max="5" data-num="1" /></div>
          </div>
        </details>
      </details>
    </section>

    <section class="vc-card">
      <h3>${icon("captions")} Captions</h3>
      <div class="vc-field">
        <label for="whisper_backend">Whisper Backend</label>
        <div class="vc-field-control">
          <select class="vc-select" id="whisper_backend" name="whisper_backend"></select>
          <label class="vc-switch"><input type="checkbox" id="enable_captions" name="enable_captions" /><span class="vc-switch-track"></span><span>Enable Captions</span></label>
        </div>
      </div>
      <div class="vc-field">
        <label for="translate_target">Translate Subtitles To</label>
        <select class="vc-select" id="translate_target" name="translate_target">
          <option>None</option><option>pt</option><option>en</option><option>es</option><option>fr</option>
          <option>de</option><option>it</option><option>ru</option><option>ja</option><option>ko</option><option>zh-CN</option>
        </select>
      </div>
      <details class="vc-nested">
        <summary>${icon("subtitles")} Subtitle Settings (alpha)</summary>
        <div class="vc-field">
          <label for="subtitle_preset">Quick Presets</label>
          <div class="vc-field-control">
            <select class="vc-select" id="subtitle_preset" name="subtitle_preset"></select>
            <label class="vc-switch"><input type="checkbox" id="use_custom_subs" name="use_custom_subs" /><span class="vc-switch-track"></span><span>Customize</span></label>
          </div>
        </div>
        <div class="vc-preview-block">
          <div class="vc-preview-toolbar">
            <span class="vc-preview-title">${icon("video")} Animated Preview</span>
            <button type="button" class="vc-btn vc-btn-primary" id="preview-video-btn">Render Animated Preview</button>
          </div>
          <div id="subtitle-preview" class="vc-preview-stage"></div>
          <video id="subtitle-preview-video" class="vc-preview-video" controls hidden></video>
        </div>
        <details class="vc-nested vc-nested-sub">
          <summary>Advanced Settings</summary>
          <div class="vc-compact-grid">
            <div class="vc-field"><label for="font_name">Font Name</label><input class="vc-input" id="font_name" name="font_name" /></div>
            <div class="vc-field"><label for="font_size">Font Size</label><input class="vc-input" id="font_size" name="font_size" type="number" min="8" max="80" data-num="1" /></div>
            <div class="vc-field"><label for="highlight_size">Highlight Size</label><input class="vc-input" id="highlight_size" name="highlight_size" type="number" min="8" max="80" data-num="1" /></div>
            <div class="vc-field"><label for="mode">Mode</label>
              <select class="vc-select" id="mode" name="mode"><option value="highlight">Highlight</option><option value="word_by_word">Word by Word</option><option value="no_highlight">No Highlight</option></select>
            </div>
            <div class="vc-field"><label for="font_color">Base Color</label><input class="vc-input" id="font_color" name="font_color" type="color" /></div>
            <div class="vc-field"><label for="highlight_color">Highlight Color</label><input class="vc-input" id="highlight_color" name="highlight_color" type="color" /></div>
            <div class="vc-field"><label for="outline_color">Outline Color</label><input class="vc-input" id="outline_color" name="outline_color" type="color" /></div>
            <div class="vc-field"><label for="shadow_color">Shadow Color</label><input class="vc-input" id="shadow_color" name="shadow_color" type="color" /></div>
            <div class="vc-field"><label for="outline_thickness">Outline Thickness</label><input class="vc-input" id="outline_thickness" name="outline_thickness" type="number" step="0.5" min="0" max="10" data-num="1" /></div>
            <div class="vc-field"><label for="shadow_size">Shadow Size</label><input class="vc-input" id="shadow_size" name="shadow_size" type="number" min="0" max="10" data-num="1" /></div>
            <div class="vc-field"><label for="border_s">Border Style</label>
              <select class="vc-select" id="border_s" name="border_s"><option value="1">Outline</option><option value="3">Opaque Box</option></select>
            </div>
            <div class="vc-field"><label for="alignment">Alignment</label>
              <select class="vc-select" id="alignment" name="alignment"><option value="1">Left</option><option value="2">Center</option><option value="3">Right</option></select>
            </div>
            <div class="vc-field"><label for="vertical_pos">V-Pos</label><input class="vc-input" id="vertical_pos" name="vertical_pos" type="number" min="0" max="500" data-num="1" /></div>
            <div class="vc-field"><label for="gap">Gap Limit</label><input class="vc-input" id="gap" name="gap" type="number" step="0.1" min="0" max="5" data-num="1" /></div>
            <div class="vc-field"><label for="w_block">Words per Block</label><input class="vc-input" id="w_block" name="w_block" type="number" min="1" max="20" data-num="1" /></div>
          </div>
          <div class="vc-compact-row" style="margin-top:10px">
            <label class="vc-switch"><input type="checkbox" id="is_bold" name="is_bold" /><span class="vc-switch-track"></span><span>Bold</span></label>
            <label class="vc-switch"><input type="checkbox" id="is_italic" name="is_italic" /><span class="vc-switch-track"></span><span>Italic</span></label>
            <label class="vc-switch"><input type="checkbox" id="is_uppercase" name="is_uppercase" /><span class="vc-switch-track"></span><span>Uppercase</span></label>
            <label class="vc-switch"><input type="checkbox" id="remove_punc" name="remove_punc" /><span class="vc-switch-track"></span><span>Remove Punctuation</span></label>
            <label class="vc-switch"><input type="checkbox" id="under" name="under" /><span class="vc-switch-track"></span><span>Underline</span></label>
            <label class="vc-switch"><input type="checkbox" id="strike" name="strike" /><span class="vc-switch-track"></span><span>Strikeout</span></label>
          </div>
        </details>
      </details>
    </section>
  </div>
<div class="vc-section-divider"><span>03</span><div><strong>Output</strong><small>Start processing and follow the render in real time.</small></div></div>
  <section class="vc-card vc-generate" id="generate-card" data-state="idle">
    <h3>${icon("generate")} Generate</h3>
    <div class="vc-generate-bar">
      <div class="vc-generate-meta">
        <span class="vc-generate-dot" aria-hidden="true"></span>
        <div>
          <strong id="generate-state">Ready</strong>
          <small id="generate-hint">Queue a render when the source and captions look right.</small>
        </div>
      </div>
      <div class="vc-generate-actions">
        <button type="button" class="vc-btn vc-btn-primary vc-btn-generate" id="start-btn">
          ${icon("actions")}
          <span id="start-btn-label">Start Processing</span>
        </button>
        <button type="button" class="vc-btn vc-btn-stop vc-btn-generate" id="stop-btn" hidden>
          ${icon("stop")}
          <span>Stop</span>
        </button>
      </div>
    </div>
    <div class="vc-console">
      <div class="vc-console-head">
        <span class="vc-console-title">${icon("terminal")} Console</span>
        <span class="vc-console-live" id="generate-live" hidden>Live</span>
      </div>
      <textarea class="vc-textarea vc-console-body" id="logs" readonly placeholder="Output appears here once processing starts."></textarea>
    </div>
    <div class="vc-output-clips" id="results-wrap" hidden>
      <div class="vc-preview-title">${icon("gallery")} Output clips</div>
      <div id="results"></div>
    </div>
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

function bindCropRisk() {
  const range = $("max_text_frame_percent");
  const num = $("max_text_frame_percent_num");
  const reset = $("crop-risk-reset");
  if (!range || !num || !reset) return;
  const def = Number(range.closest(".vc-slider")?.dataset.default || 15);
  const paint = (value) => {
    const v = Math.max(0, Math.min(100, Number(value) || 0));
    range.value = v;
    num.value = v;
    range.style.background = `linear-gradient(90deg, var(--vc-primary) ${v}%, var(--vc-border-strong) ${v}%)`;
  };
  paint(range.value);
  range.addEventListener("input", () => paint(range.value));
  num.addEventListener("input", () => paint(num.value));
  num.addEventListener("change", () => range.dispatchEvent(new Event("change", { bubbles: true })));
  reset.addEventListener("click", () => {
    paint(def);
    range.dispatchEvent(new Event("change", { bubbles: true }));
  });
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
  bindCropRisk();
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

function setGenerateState(state, title, hint) {
  const card = $("generate-card");
  if (card) card.dataset.state = state;
  const label = $("generate-state");
  const note = $("generate-hint");
  const live = $("generate-live");
  if (label) label.textContent = title;
  if (note) note.textContent = hint;
  if (live) live.hidden = state !== "running";
}

async function startJob() {
  const startBtn = $("start-btn");
  const startLabel = $("start-btn-label");
  const stopBtn = $("stop-btn");
  const logs = $("logs");
  const finish = (state, title, hint) => {
    startBtn.disabled = false;
    if (startLabel) startLabel.textContent = "Start Processing";
    stopBtn.hidden = true;
    setGenerateState(state, title, hint);
  };
  startBtn.disabled = true;
  if (startLabel) startLabel.textContent = "Running…";
  stopBtn.hidden = false;
  logs.value = "";
  $("results").innerHTML = "";
  $("results-wrap").hidden = true;
  setGenerateState("running", "Processing", "Streaming encoder output in real time.");
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
        $("results").innerHTML = data.gallery_html || "";
        $("results-wrap").hidden = !data.gallery_html;
        finish("done", data.gallery_html ? "Complete" : "Finished", data.gallery_html ? "Clips are ready below." : "No clips were produced.");
      }
    };
    source.onerror = () => {
      source.close();
      finish("error", "Disconnected", "The live stream closed before the job finished.");
    };
  } catch (err) {
    logs.value = err.message;
    finish("error", "Failed", err.message);
  }
}
