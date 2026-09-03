import gradio as gr
import subprocess
import os
import sys
import json
import psutil
import shutil
import datetime
import time
import urllib.parse
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn


import re
import library # Module for Library Logic
import subtitle_handler as subs # Module for Subtitles
import subtitle_editor as editor # Module for Editor Logic
import ui_settings as ui_cfg
import generation_profiles

# Path to the main script
MAIN_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main_improved.py")
WORKING_DIR = os.path.dirname(MAIN_SCRIPT_PATH)
sys.path.append(WORKING_DIR)

from i18n.i18n import I18nAuto
i18n = I18nAuto()

# --- PRESETS DEFINITIONS ---
FACE_PRESETS = generation_profiles.FACE_PRESETS

EXPERIMENTAL_PRESETS = {
    "Default (Off)": {"focus": False, "mar": 0.03, "score": 1.5, "motion": False, "motion_th": 3.0, "motion_sens": 0.05, "decay": 2.0},
    "Active Speaker (Balanced)": {"focus": True, "mar": 0.03, "score": 1.5, "motion": True, "motion_th": 3.0, "motion_sens": 0.05, "decay": 2.0},
    "Active Speaker (Sensitive)": {"focus": True, "mar": 0.02, "score": 1.0, "motion": True, "motion_th": 2.0, "motion_sens": 0.10, "decay": 1.0},
    "Active Speaker (Stable)": {"focus": True, "mar": 0.05, "score": 2.5, "motion": False, "motion_th": 5.0, "motion_sens": 0.02, "decay": 3.0},
}
# ---------------------------

VIRALS_DIR = os.path.join(WORKING_DIR, "VIRALS")
MODELS_DIR = os.path.join(WORKING_DIR, "models")

# Ensure directories exist
if not os.path.exists(VIRALS_DIR):
    os.makedirs(VIRALS_DIR, exist_ok=True)
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR, exist_ok=True)

# Global variables
current_process = None

# Helpers
def convert_color_to_ass(hex_color, alpha="00"):
    if not hex_color:
        return f"&H{alpha}FFFFFF&"

    hex_clean = hex_color.lstrip("#").strip()

    if hex_clean.lower().startswith("rgb"):
        try:
            values = re.findall(r"[\d.]+", hex_clean)
            if len(values) >= 3:
                red, green, blue = (
                    max(0, min(255, int(float(value)))) for value in values[:3]
                )
                return f"&H{alpha}{blue:02X}{green:02X}{red:02X}&".upper()
        except (TypeError, ValueError):
            return f"&H{alpha}FFFFFF&"

    if len(hex_clean) == 3:
        hex_clean = "".join(character * 2 for character in hex_clean)

    if len(hex_clean) == 6 and re.fullmatch(r"[0-9a-fA-F]{6}", hex_clean):
        red, green, blue = hex_clean[0:2], hex_clean[2:4], hex_clean[4:6]
        return f"&H{alpha}{blue}{green}{red}&".upper()

    return f"&H{alpha}FFFFFF&"
def kill_process():
    global current_process
    if current_process:
        try:
            parent = psutil.Process(current_process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            current_process = None
            return i18n("Process terminated.")
        except Exception as e:
            return i18n("Error terminating process: {}").format(e)
    return i18n("No process running.")

GEMINI_MODELS = [
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-3.5-flash',
]

G4F_MODELS = [
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4',
    'o1-mini',
    'o1',
    'deepseek-r1',
    'deepseek-v3',
    'llama-3.3-70b',
    'llama-3.1-405b',
    'claude-3.5-sonnet',
    'claude-3.7-sonnet',
    'gemini-2.0-flash',
    'qwen-2.5-72b'
]

GROQ_MODELS = [
    'openai/gpt-oss-120b'
]

CLOUDFLARE_MODELS = [
    '@cf/openai/gpt-oss-120b'
]

WHISPER_BACKENDS = [
    'cloudflare',
    'groq',
    'azure'
]



def apply_face_preset(preset_name):
    if preset_name not in FACE_PRESETS:
        return [gr.update() for _ in range(4)] # No change
    
    p = FACE_PRESETS[preset_name]
    return p["thresh"], p["two_face"], p["conf"], p["dead_zone"]


def apply_generation_profile(profile_name):
    profile = generation_profiles.resolve_generation_profile(profile_name)
    if not profile:
        return [gr.update() for _ in range(11)]
    return (
        profile["segments"], profile["min_duration"], profile["max_duration"],
        profile["face_mode"], profile["face_detect_interval"], profile["no_face_mode"],
        profile["face_preset"], profile["thresh"], profile["two_face"],
        profile["conf"], profile["dead_zone"],
    )

def apply_experimental_preset(preset_name):
    if preset_name not in EXPERIMENTAL_PRESETS:
        return [gr.update() for _ in range(7)] # No change
        
    p = EXPERIMENTAL_PRESETS[preset_name]
    return p["focus"], p["mar"], p["score"], p["motion"], p["motion_th"], p["motion_sens"], p["decay"]

# Subtitle logic moved to subtitle_handler.py


def run_viral_cutter(input_source, project_name, url, video_file, segments, viral, themes, min_duration, max_duration, text_safe_selection, max_text_frame_percent, generation_profile, model, ai_backend, api_key, ai_model_name, chunk_size, workflow, face_model, face_mode, face_detect_interval, no_face_mode,
                     face_filter_thresh, face_two_thresh, face_conf_thresh, face_dead_zone, focus_active_speaker, active_speaker_mar, active_speaker_score_diff, include_motion, active_speaker_motion_threshold, active_speaker_motion_sensitivity, active_speaker_decay,
                     enable_captions, use_custom_subs, font_name, font_size, font_color, highlight_color, outline_color, outline_thickness, shadow_color, shadow_size, is_bold, is_italic, is_uppercase, vertical_pos, alignment,
                     h_size, w_block, gap, mode, under, strike, border_s, remove_punc, video_quality, use_youtube_subs, translate_target,
                     face_preset, experimental_preset, subtitle_preset):
    
    global current_process

    ui_cfg.persist_create_tab_settings(
        api_key,
        input_source, video_quality, translate_target, use_youtube_subs, segments, viral, themes,
        min_duration, max_duration, text_safe_selection, max_text_frame_percent, generation_profile,
        ai_backend, ai_model_name, chunk_size, model, enable_captions, workflow,
        face_model, face_mode, face_detect_interval, no_face_mode,
        face_preset, face_filter_thresh, face_two_thresh, face_conf_thresh, face_dead_zone,
        experimental_preset, focus_active_speaker, active_speaker_mar, active_speaker_score_diff,
        include_motion, active_speaker_motion_threshold, active_speaker_motion_sensitivity, active_speaker_decay,
        subtitle_preset, use_custom_subs, font_name, font_size, font_color, highlight_color,
        outline_color, outline_thickness, shadow_color, shadow_size, is_bold, is_italic, is_uppercase,
        h_size, w_block, gap, mode, under, strike, border_s, vertical_pos, alignment, remove_punc,
    )

    yield "", gr.update(value=i18n("Running..."), interactive=False), gr.update(visible=True), None 

    cmd = [sys.executable, MAIN_SCRIPT_PATH]
    
    # Input Source Logic
    if input_source == "Existing Project":
        if not project_name:
             yield i18n("Error: No project selected."), gr.update(value=i18n("Start Processing"), interactive=True), gr.update(visible=False), None
             return
        full_project_path = os.path.join(VIRALS_DIR, project_name)
        cmd.extend(["--project-path", full_project_path])
    elif input_source == "Upload Video":
        if not video_file:
             yield i18n("Error: No video file uploaded."), gr.update(value=i18n("Start Processing"), interactive=True), gr.update(visible=False), None
             return
        
        # Determine project name from filename
        original_filename = os.path.basename(video_file)
        name_no_ext = os.path.splitext(original_filename)[0]
        # Sanitize: Allow alphanumeric, space, dash, underscore
        safe_name = "".join([c for c in name_no_ext if c.isalnum() or c in " _-"]).strip()
        if not safe_name: safe_name = "Untitled_Upload"
        
        # Always append timestamp as requested
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name_upload = f"{safe_name}_{timestamp}"
        project_path = os.path.join(VIRALS_DIR, project_name_upload)
             
        os.makedirs(project_path, exist_ok=True)
        
        target_path = os.path.join(project_path, "input.mp4")
        shutil.copy(video_file, target_path)
        
        cmd.extend(["--project-path", project_path])
        # Skip YouTube subs as it is a local upload
        cmd.append("--skip-youtube-subs")
        
    else:
        if url: cmd.extend(["--url", url])
        # Pass Video Quality
        if video_quality: cmd.extend(["--video-quality", video_quality])
        # Pass Subtitle Option (if False, we skip)
        if not use_youtube_subs: cmd.append("--skip-youtube-subs")
        
    # Translation
    if translate_target and translate_target != "None":
            cmd.extend(["--translate-target", translate_target])

    
    cmd.extend(["--segments", str(int(segments))])
    if viral: cmd.append("--viral")
    if themes: cmd.extend(["--themes", themes])
    cmd.extend(["--min-duration", str(int(min_duration))])
    cmd.extend(["--max-duration", str(int(max_duration))])
    if text_safe_selection:
        cmd.append("--text-safe-selection")
        cmd.extend(["--max-text-frame-percent", str(float(max_text_frame_percent))])
    cmd.extend(["--model", model])
    cmd.extend(["--ai-backend", ai_backend])
    if api_key: cmd.extend(["--api-key", api_key])
    if not enable_captions:
        cmd.append("--no-subtitles")
        cmd.append("--skip-youtube-subs")
    
    # New AI Params
    if ai_model_name: cmd.extend(["--ai-model-name", str(ai_model_name)])
    if chunk_size: cmd.extend(["--chunk-size", str(int(chunk_size))])

    workflow_map = {"Full": "1", "Cut Only": "2", "Subtitles Only": "3"}
    cmd.extend(["--workflow", workflow_map.get(workflow, "1")])
    cmd.extend(["--face-model", face_model])
    cmd.extend(["--face-mode", face_mode])
    if face_detect_interval: cmd.extend(["--face-detect-interval", str(face_detect_interval)])
    if no_face_mode: cmd.extend(["--no-face-mode", no_face_mode])
    
    # New Face Params
    if face_filter_thresh is not None: cmd.extend(["--face-filter-threshold", str(face_filter_thresh)])
    if face_two_thresh is not None: cmd.extend(["--face-two-threshold", str(face_two_thresh)])
    if face_conf_thresh is not None: cmd.extend(["--face-confidence-threshold", str(face_conf_thresh)])
    if face_dead_zone is not None: cmd.extend(["--face-dead-zone", str(face_dead_zone)])


    
    cmd.append("--skip-prompts")
    
    if focus_active_speaker:
        cmd.append("--focus-active-speaker")
        if active_speaker_mar is not None: cmd.extend(["--active-speaker-mar", str(active_speaker_mar)])
        if active_speaker_score_diff is not None: cmd.extend(["--active-speaker-score-diff", str(active_speaker_score_diff)])
        if include_motion: cmd.append("--include-motion")
        if active_speaker_motion_threshold is not None: cmd.extend(["--active-speaker-motion-threshold", str(active_speaker_motion_threshold)])
        if active_speaker_motion_sensitivity is not None: cmd.extend(["--active-speaker-motion-sensitivity", str(active_speaker_motion_sensitivity)])
        if active_speaker_decay is not None: cmd.extend(["--active-speaker-decay", str(active_speaker_decay)])

    cmd.append("--skip-prompts") # Always skip prompts in WebUI to prevent freezing

    if use_custom_subs:
        subtitle_config = {
            "font": font_name, "base_size": int(font_size), "base_color": convert_color_to_ass(font_color), "highlight_color": convert_color_to_ass(highlight_color),
            "outline_color": convert_color_to_ass(outline_color), "outline_thickness": outline_thickness, "shadow_color": convert_color_to_ass(shadow_color),
            "shadow_size": shadow_size, "vertical_position": vertical_pos, "alignment": alignment, "bold": 1 if is_bold else 0, "italic": 1 if is_italic else 0, 
            "underline": 1 if under else 0, "strikeout": 1 if strike else 0, "border_style": border_s, "words_per_block": int(w_block), "gap_limit": gap,
            "mode": mode, "highlight_size": int(h_size), "remove_punctuation": remove_punc
        }
        # Uppercase is handled in main script or logic? 
        # Actually subtitle_config doesn't seem to natively support "uppercase" in get_subtitle_config default, but app.py was using it. 
        # I should probably add it back if I want to support it, but user said "PROHIBITED to remove existing ones".
        # I'll re-add 'uppercase': 1 if is_uppercase else 0 to the dict if the backend supports it, otherwise it's just ignored.
        # But wait, main_improved.py doesn't have 'uppercase' in get_subtitle_config. 
        # I'll keep it in the dict just in case logic uses it elsewhere or if I missed it.
        # Actually, standard ASS doesn't support uppercase flag directly in Style, it needs to be text transform.
        # But I'll leave it in the dict.
        subtitle_config["uppercase"] = 1 if is_uppercase else 0

        subtitle_config_path = os.path.join(WORKING_DIR, "temp_subtitle_config.json")
        try:
            with open(subtitle_config_path, "w", encoding="utf-8") as f:
                json.dump(subtitle_config, f, indent=4)
            cmd.extend(["--subtitle-config", subtitle_config_path])
        except Exception: pass 
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    try:
        current_process = subprocess.Popen(cmd, cwd=WORKING_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, env=env)
        logs = ""
        project_folder_path = None
        if input_source == "Existing Project" and project_name:
             # If using existing project, we already know the path, but let's see if logs confirm it
             project_folder_path = os.path.join(VIRALS_DIR, project_name)

        last_update_time = time.time()
        
        while True:
            line = current_process.stdout.readline()
            if not line and current_process.poll() is not None:
                break
            
            if line:
                logs += line
                if "Project Folder:" in line:
                    parts = line.split("Project Folder:")
                    if len(parts) > 1: project_folder_path = parts[1].strip()
                
                # Throttle updates to avoid browser freeze (0.2s interval)
                current_time = time.time()
                if current_time - last_update_time > 0.2:
                    yield logs, gr.update(visible=True, interactive=False), gr.update(visible=True), None
                    last_update_time = current_time
        
        # Final yield to ensure all logs are shown
        yield logs, gr.update(visible=True, interactive=False), gr.update(visible=True), None
    except Exception as e:
        logs += f"\nError running process: {str(e)}\n"
        yield logs, gr.update(visible=True, interactive=False), gr.update(visible=True), None
    finally:
        if current_process:
            if current_process.stdout:
                try:
                    current_process.stdout.close()
                except Exception: pass
            if current_process.poll() is None:
                # If we are here, it means we finished reading or errored out, but process is still running.
                # If it was a normal break from loop, process should be done or close to done.
                # If we are stopping, current_process.terminate() might be needed outside? 
                # But here we just wait.
                try:
                    current_process.wait()
                except Exception: pass
            current_process = None
    
    # Wait to ensure filesystem flush
    time.sleep(1.0)
    
    html_output = ""
    if project_folder_path and os.path.exists(project_folder_path):
        html_output = library.generate_project_gallery(project_folder_path, is_full_path=True)
    else:
        html_output = f"<h3>{i18n('Error: Project folder could not be determined from logs.')}</h3>"
    yield logs, gr.update(value=i18n("Start Processing"), interactive=True), gr.update(visible=False), html_output

THEME_CSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme.css")
with open(THEME_CSS_PATH, encoding="utf-8") as theme_file:
    css = theme_file.read()

import header

ui_state = ui_cfg.load_ui_state()
saved_theme = ui_state.get("theme", "dark")
if saved_theme not in ("dark", "light"):
    saved_theme = "dark"

head_script = (
    "<script>(function(){var t=localStorage.getItem('vc-theme')||'"
    + saved_theme
    + "';document.documentElement.setAttribute('data-theme',t);"
    "document.documentElement.classList.toggle('dark',t==='dark');})();</script>"
)

theme_init_js = (
    "() => { const t = localStorage.getItem('vc-theme') || '"
    + saved_theme
    + "'; document.documentElement.setAttribute('data-theme', t);"
    " document.documentElement.classList.toggle('dark', t === 'dark');"
    " if (document.body) { document.body.setAttribute('data-theme', t);"
    " document.body.classList.toggle('dark', t === 'dark'); }"
    " document.addEventListener('focusin', (e) => {"
    " const el = e.target;"
    " if (el && el.matches && el.matches('#vc-ai-backend-control input[role=\"combobox\"], #vc-ai-model-control input[role=\"combobox\"], #vc-video-quality-control input[role=\"combobox\"]')) el.setAttribute('readonly', 'readonly');"
    " }, true); }"
)

THEME_CLICK_JS = """
(current) => {
  const next = current === 'light' ? 'dark' : 'light';
  const root = document.documentElement;
  root.setAttribute('data-theme', next);
  root.classList.toggle('dark', next === 'dark');
  if (document.body) {
    document.body.setAttribute('data-theme', next);
    document.body.classList.toggle('dark', next === 'dark');
  }
  document.querySelectorAll('.gradio-container').forEach((el) => {
    el.setAttribute('data-theme', next);
    el.classList.toggle('dark', next === 'dark');
  });
  localStorage.setItem('vc-theme', next);
  return [next, next === 'light' ? 'Dark' : 'Light'];
}
"""

vc_theme = gr.themes.Default(
    primary_hue="teal",
    neutral_hue="slate",
    font=gr.themes.GoogleFont("Manrope"),
)

with gr.Blocks(title=i18n("ViralCutter WebUI"), theme=vc_theme, css=css, head=head_script, js=theme_init_js) as demo:
    theme_state = gr.State(saved_theme)
    with gr.Row(elem_classes=["vc-appbar-row"]):
        gr.HTML(header.brand_html())
        theme_btn = gr.Button(
            "Dark" if saved_theme == "light" else "Light",
            elem_id="vc-theme-toggle",
            size="sm",
            scale=0,
        )
    theme_btn.click(
        fn=None,
        inputs=[theme_state],
        outputs=[theme_state, theme_btn],
        js=THEME_CLICK_JS,
    )
    theme_state.change(
        lambda theme: ui_cfg.save_ui_state({"theme": theme}) if theme in ("dark", "light") else None,
        inputs=theme_state,
        outputs=None,
        queue=False,
        show_progress="hidden",
    )

    gr.HTML("""
<section class="vc-workspace-heading" id="vc-workspace">
  <div>
    <span class="vc-eyebrow">New production</span>
    <h1>Create your next short</h1>
    <p>Choose the source, tune clip selection, and control framing and captions in one focused workspace.</p>
  </div>
  <div class="vc-workspace-meta"><span>01</span><small>Workspace</small></div>
</section>
""")

    with gr.Row(elem_id="vc-workspace-nav", elem_classes=["vc-workspace-nav"]):
        nav_create_btn = gr.Button(
            i18n("Create New"),
            elem_id="vc-nav-create",
            elem_classes=["vc-nav-item", "vc-nav-active"],
        )
        nav_editor_btn = gr.Button(
            i18n("Subtitle Editor"),
            elem_id="vc-nav-editor",
            elem_classes=["vc-nav-item"],
        )
        nav_library_btn = gr.Button(
            i18n("Library"),
            elem_id="vc-nav-library",
            elem_classes=["vc-nav-item"],
        )

    with gr.Tabs(selected="create", elem_id="vc-main-tabs") as main_tabs:
        with gr.Tab(i18n("Create New"), id="create"):
             with gr.Row(equal_height=False, elem_classes=["vc-core-grid"]):
                with gr.Column(scale=1, elem_classes=["vc-stack"]):
                    with gr.Group(elem_classes=["vc-card", "vc-card-video"]):
                        gr.Markdown(f"### {i18n('Video')}")
                        input_source = gr.Radio(
                            [(i18n("YouTube URL"), "YouTube URL"), (i18n("Existing Project"), "Existing Project"), (i18n("Upload Video"), "Upload Video")],
                            label=i18n("Input Source"),
                            value=ui_state.get("input_source", "YouTube URL"),
                            elem_id="vc-input-source",
                        )
                        url_input = gr.Textbox(
                            label=i18n("YouTube URL"),
                            placeholder="https://www.youtube.com/watch?v=...",
                            visible=True,
                            elem_id="vc-youtube-url",
                        )
                        video_upload = gr.File(label=i18n("Upload Video"), file_count="single", file_types=["video"], visible=False)
                        with gr.Row(elem_id="vc-video-quality-row"):
                            video_quality_input = gr.Dropdown(
                                choices=[(i18n("Best Quality"), "best"), "1080p", "720p", "480p"],
                                label=i18n("Video Quality"),
                                value=ui_state.get("video_quality", "best"),
                                scale=2,
                                elem_id="vc-video-quality-control",
                                elem_classes=["vc-compact-control", "vc-video-quality-control"],
                            )
                            with gr.Column(scale=3, elem_id="vc-youtube-subs-field"):
                                use_youtube_subs_input = gr.Checkbox(
                                    label=i18n("Use YouTube Subs"),
                                    value=ui_state.get("use_youtube_subs", True),
                                )
                                gr.Markdown(
                                    i18n("Download and use official subtitles if available. (Recommended, it speeds up the process)"),
                                    elem_classes=["vc-field-help"],
                                )
                        project_selector = gr.Dropdown(choices=[], label=i18n("Select Project"), visible=False)

                    def on_source_change(source):
                        if source == "YouTube URL":
                            return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(value="Full")
                        elif source == "Upload Video":
                             return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(value="Full")
                        else:
                            projs = library.get_existing_projects()
                            return gr.update(visible=False), gr.update(choices=projs, visible=True), gr.update(visible=False), gr.update(value="Subtitles Only")

                with gr.Column(scale=1, elem_classes=["vc-stack"]):
                    with gr.Group(elem_classes=["vc-card", "vc-card-api"]):
                        gr.Markdown(f"### {i18n('API')}")
                        with gr.Row():
                            ai_backend_input = gr.Dropdown(choices=[(i18n("Gemini"), "gemini"), (i18n("Groq"), "groq"), (i18n("Cloudflare"), "cloudflare"), (i18n("G4F"), "g4f"), (i18n("Manual"), "manual")], label=i18n("AI Backend"), value=ui_state.get("ai_backend", "gemini"), scale=2, elem_id="vc-ai-backend-control", elem_classes=["vc-compact-control", "vc-ai-backend-control"])
                            api_key_input = gr.Textbox(label=i18n("Gemini API Key"), type="password", value=ui_cfg.load_saved_api_key(ui_state.get("ai_backend", "gemini")), scale=3)
                        with gr.Row(elem_id="vc-ai-model-row"):
                            ai_model_input = gr.Dropdown(choices=GEMINI_MODELS, label=i18n("AI Model"), value=ui_state.get("ai_model_name", GEMINI_MODELS[0]), allow_custom_value=True, visible=True, scale=4, elem_id="vc-ai-model-control", elem_classes=["vc-compact-control", "vc-ai-model-control"])
                            chunk_size_input = gr.Number(label=i18n("Chunk Size"), value=ui_state.get("chunk_size", 70000), precision=0, scale=1, elem_id="vc-chunk-size-control", elem_classes=["vc-chunk-size-control"])

                    def update_ai_ui(backend):
                        show_api = backend in ("gemini", "groq")
                        api_label = i18n("Groq API Key") if backend == "groq" else i18n("Gemini API Key")
                        saved = ui_cfg.load_ui_state()
                        new_choices = []
                        new_val = saved.get("ai_model_name", "")
                        new_chunk = saved.get("chunk_size", 70000)

                        if backend == "gemini":
                            new_choices = GEMINI_MODELS
                            new_val = new_val if new_val in GEMINI_MODELS else GEMINI_MODELS[0]
                            new_chunk = saved.get("chunk_size", 70000)
                        elif backend == "g4f":
                            new_choices = G4F_MODELS
                            new_val = new_val if new_val in G4F_MODELS else G4F_MODELS[5]
                            new_chunk = saved.get("chunk_size", 70000)
                        elif backend == "groq":
                            new_choices = GROQ_MODELS
                            new_val = new_val if new_val in GROQ_MODELS else GROQ_MODELS[0]
                            new_chunk = saved.get("chunk_size", 40000)
                        elif backend == "cloudflare":
                            new_choices = CLOUDFLARE_MODELS
                            new_val = new_val if new_val in CLOUDFLARE_MODELS else CLOUDFLARE_MODELS[0]
                            new_chunk = saved.get("chunk_size", 40000)

                        return (
                            gr.update(visible=show_api, label=api_label, value=ui_cfg.load_saved_api_key(backend)),
                            gr.update(choices=new_choices, value=new_val, visible=(backend != "manual")),
                            gr.update(value=new_chunk)
                        )

                    ai_backend_input.change(update_ai_ui, inputs=ai_backend_input, outputs=[api_key_input, ai_model_input, chunk_size_input], show_progress="hidden")

                    def update_gemini_chunk(model_name):
                        if model_name and "pro" in str(model_name).lower() and "flash" not in str(model_name).lower():
                            return gr.update(value=20000)
                        return gr.update(value=70000)

                    ai_model_input.change(update_gemini_chunk, inputs=ai_model_input, outputs=chunk_size_input, show_progress="hidden")

             gr.HTML("""
<div class="vc-section-divider"><span>02</span><div><strong>Processing</strong><small>Choose how clips are detected, framed, and transcribed.</small></div></div>
""")
             with gr.Row(equal_height=False, elem_classes=["vc-core-grid", "vc-processing-grid"]):
                with gr.Column(scale=3, elem_classes=["vc-stack"]):
                    with gr.Group(elem_classes=["vc-card", "vc-card-cutting"]):
                        gr.Markdown(f"### {i18n('Cutting')}")
                        generation_profile_input = gr.Dropdown(
                            choices=[(i18n(name), name) for name in generation_profiles.GENERATION_PROFILES],
                            label=i18n("Generation Profile"),
                            value=ui_state.get("generation_profile", "Custom"),
                            info=i18n("Sets clip count, duration, face mode, tracking speed, and face preset together."),
                            elem_classes=["vc-compact-control", "vc-profile-control"],
                        )
                        with gr.Row():
                            segments_input = gr.Number(label=i18n("Segments"), value=ui_state.get("segments", 3), precision=0)
                            viral_input = gr.Checkbox(label=i18n("Viral Mode"), value=ui_state.get("viral", True))
                        themes_input = gr.Textbox(label=i18n("Themes"), placeholder=i18n("funny, sad..."), value=ui_state.get("themes", ""), visible=not ui_state.get("viral", True))
                        viral_input.change(lambda x: gr.update(visible=not x), viral_input, themes_input)
                        with gr.Row():
                            min_dur_input = gr.Number(label=i18n("Min Duration (s)"), value=ui_state.get("min_duration", 15))
                            max_dur_input = gr.Number(label=i18n("Max Duration (s)"), value=ui_state.get("max_duration", 90))
                        text_safe_selection_input = gr.Checkbox(
                            label=i18n("Text Safe Selection"),
                            value=ui_state.get("text_safe_selection", False),
                        )
                        max_text_frame_percent_input = gr.Slider(
                            label=i18n("Crop-Risk Text Max (%)"),
                            minimum=0,
                            maximum=100,
                            value=ui_state.get("max_text_frame_percent", 15),
                            step=1,
                        )
                with gr.Column(scale=2, elem_classes=["vc-stack"]):
                    with gr.Group(elem_classes=["vc-card", "vc-card-captions"]):
                        gr.Markdown(f"### {i18n('Captions')}")
                        with gr.Row():
                            model_input = gr.Dropdown(WHISPER_BACKENDS, label=i18n("Whisper Backend"), value=ui_state.get("whisper_backend", "cloudflare"))
                            enable_captions_input = gr.Checkbox(
                                label=i18n("Enable Captions"),
                                value=ui_state.get("enable_captions", True),
                            )
                        translate_input = gr.Dropdown(choices=["None", "pt", "en", "es", "fr", "de", "it", "ru", "ja", "ko", "zh-CN"], label=i18n("Translate Subtitles To"), value=ui_state.get("translate_target", "None"), elem_classes=["vc-compact-control", "vc-translate-control"])

             with gr.Group(elem_classes=["vc-card", "vc-card-wide"]):
                gr.Markdown(f"### {i18n('Face / Vertical')}")
                with gr.Row():
                    workflow_input = gr.Dropdown(choices=[(i18n("Full"), "Full"), (i18n("Cut Only"), "Cut Only"), (i18n("Subtitles Only"), "Subtitles Only")], label=i18n("Workflow"), value=ui_state.get("workflow", "Full"))
                    face_model_input = gr.Dropdown(["insightface", "mediapipe"], label=i18n("Face Model"), value=ui_state.get("face_model", "insightface"))
                    face_mode_input = gr.Dropdown(
                        choices=[
                            (i18n("Auto"), "auto"),
                            ("1", "1"),
                            ("2", "2"),
                            (i18n("Fixed Center (No Tracking)"), "fixed_center"),
                        ],
                        label=i18n("Face Mode"),
                        value=ui_state.get("face_mode", "auto"),
                    )
                with gr.Row():
                    face_detect_interval_input = gr.Textbox(label=i18n("Face Det. Interval"), value=ui_state.get("face_detect_interval", "0.17,0.35"))
                    no_face_mode_input = gr.Dropdown(choices=[(i18n("Padding (9:16)"), "padding"), (i18n("Zoom (Center)"), "zoom")], label=i18n("No Face Fallback"), value=ui_state.get("no_face_mode", "zoom"))

             input_source.change(on_source_change, inputs=input_source, outputs=[url_input, project_selector, video_upload, workflow_input])
             demo.load(on_source_change, inputs=input_source, outputs=[url_input, project_selector, video_upload, workflow_input], queue=False, show_progress="hidden")

             with gr.Accordion(i18n("Advanced Face Settings"), open=False, elem_classes=["vc-card", "vc-advanced-card"]):
                 face_preset_input = gr.Dropdown(choices=[(i18n(k), k) for k in FACE_PRESETS.keys()], label=i18n("Configuration Presets"), value=ui_state.get("face_preset", "Default (Balanced)"), interactive=True)
                 with gr.Row(elem_classes=["vc-slider-grid"]):
                      face_filter_thresh_input = gr.Slider(label=i18n("Ignore Small Faces (0.0 - 1.0)"), minimum=0.0, maximum=1.0, value=ui_state.get("face_filter_thresh", 0.30), step=0.05, info=i18n("Relative size to ignore background."))
                      face_two_thresh_input = gr.Slider(label=i18n("Threshold for 2 Faces (0.0 - 1.0)"), minimum=0.0, maximum=1.0, value=ui_state.get("face_two_thresh", 0.60), step=0.05, info=i18n("Size of 2nd face to activate split mode."))
                      face_conf_thresh_input = gr.Slider(label=i18n("Minimum Confidence (0.0 - 1.0)"), minimum=0.0, maximum=1.0, value=ui_state.get("face_conf_thresh", 0.50), step=0.05, info=i18n("Ignore detections with low confidence."))
                      face_dead_zone_input = gr.Slider(label=i18n("Dead Zone (Stabilization)"), minimum=0, maximum=120, value=ui_state.get("face_dead_zone", 45), step=5, info=i18n("Movement pixels to ignore."))
                 
                 face_preset_input.change(apply_face_preset, inputs=face_preset_input, outputs=[face_filter_thresh_input, face_two_thresh_input, face_conf_thresh_input, face_dead_zone_input])
                 generation_profile_input.change(
                     apply_generation_profile,
                     inputs=generation_profile_input,
                     outputs=[
                         segments_input, min_dur_input, max_dur_input,
                         face_mode_input, face_detect_interval_input, no_face_mode_input,
                         face_preset_input, face_filter_thresh_input, face_two_thresh_input,
                         face_conf_thresh_input, face_dead_zone_input,
                     ],
                 )

                 with gr.Accordion(i18n("Experimental: Active Speaker & Motion"), open=False):
                        experimental_preset_input = gr.Dropdown(choices=[(i18n(k), k) for k in EXPERIMENTAL_PRESETS.keys()], label=i18n("Configuration Presets"), value=ui_state.get("experimental_preset", "Default (Off)"), interactive=True)
                        focus_active_speaker_input = gr.Checkbox(label=i18n("Experimental: Focus on Speaker"), value=ui_state.get("focus_active_speaker", False), info=i18n("Tries to focus only on the speaking person instead of split screen."))
                        with gr.Row():
                            active_speaker_mar_input = gr.Slider(label=i18n("MAR Threshold (Mouth Open)"), minimum=0.01, maximum=0.20, value=ui_state.get("active_speaker_mar", 0.03), step=0.005, info=i18n("Mouth open sensitivity."))
                            active_speaker_score_diff_input = gr.Slider(label=i18n("Score Difference"), minimum=0.5, maximum=10.0, value=ui_state.get("active_speaker_score_diff", 1.5), step=0.5, info=i18n("Minimum difference to focus on 1 face."))
                            
                        with gr.Row():
                            include_motion_input = gr.Checkbox(label=i18n("Consider Motion"), value=ui_state.get("include_motion", False), info=i18n("Increases score with motion (gestures)."))
                            
                        with gr.Row():
                            active_speaker_motion_threshold_input = gr.Slider(label=i18n("Motion Dead Zone"), minimum=0.0, maximum=20.0, value=ui_state.get("active_speaker_motion_threshold", 3.0), step=0.5, info=i18n("Pixels ignored."))
                            active_speaker_motion_sensitivity_input = gr.Slider(label=i18n("Motion Sensitivity"), minimum=0.01, maximum=0.5, value=ui_state.get("active_speaker_motion_sensitivity", 0.05), step=0.01, info=i18n("Points per pixel."))
                            active_speaker_decay_input = gr.Slider(label=i18n("Switch Speed"), minimum=0.5, maximum=5.0, value=ui_state.get("active_speaker_decay", 2.0), step=0.5, info=i18n("Speed to lose focus."))

                        experimental_preset_input.change(apply_experimental_preset, inputs=experimental_preset_input, outputs=[focus_active_speaker_input, active_speaker_mar_input, active_speaker_score_diff_input, include_motion_input, active_speaker_motion_threshold_input, active_speaker_motion_sensitivity_input, active_speaker_decay_input])
             with gr.Accordion(i18n("Subtitle Settings (alpha)"), open=False, elem_classes=["vc-card", "vc-advanced-card"]):
                preset_input = gr.Dropdown(choices=[(i18n("Manual"), "Manual")] + [(i18n(k), k) for k in subs.SUBTITLE_PRESETS.keys()], label=i18n("Quick Presets"), value=ui_state.get("subtitle_preset", "Hormozi (Classic)"))
                use_custom_subs = gr.Checkbox(label=i18n("Enable Subtitle Customization (Includes Preset)"), value=ui_state.get("use_custom_subs", True))
                
                # Previews (Always Visible)
                preview_html = gr.HTML(value=f"<div style='text-align:center; padding:10px; color:#666;'>{i18n('Select options or preset to preview')}</div>")
                
                with gr.Row():
                    preview_vid_btn = gr.Button(i18n("🎬 Render Animated Preview (Slow)"), size="sm")
                preview_vid = gr.Video(label=i18n("Animated Preview"), height=300, autoplay=True, interactive=False)
                
                with gr.Accordion(i18n("Advanced Settings"), open=False):
                    gr.Markdown(f"### {i18n('Appearance')}")
                    with gr.Row():
                        font_name_input = gr.Textbox(label=i18n("Font Name"), value=ui_state.get("font_name", "Montserrat-Regular"))
                        font_size_input = gr.Slider(label=i18n("Font Size (Base)"), minimum=8, maximum=80, value=ui_state.get("font_size", 12))
                        highlight_size_input = gr.Slider(label=i18n("Highlight Size"), minimum=8, maximum=80, value=ui_state.get("highlight_size", 14))
                    
                    with gr.Row():
                        font_color_input = gr.ColorPicker(label=i18n("Base Color"), value=ui_state.get("font_color", "#FFFFFF"))
                        highlight_color_input = gr.ColorPicker(label=i18n("Highlight Color"), value=ui_state.get("highlight_color", "#00FF00"))
                        outline_color_input = gr.ColorPicker(label=i18n("Outline Color"), value=ui_state.get("outline_color", "#000000"))
                        shadow_color_input = gr.ColorPicker(label=i18n("Shadow Color"), value=ui_state.get("shadow_color", "#000000"))
                    
                    gr.Markdown(f"### {i18n('Styling & Effects')}")
                    with gr.Row():
                        outline_thickness_input = gr.Slider(label=i18n("Outline Thickness"), minimum=0, maximum=10, value=ui_state.get("outline_thickness", 1.5))
                        shadow_size_input = gr.Slider(label=i18n("Shadow Size"), minimum=0, maximum=10, value=ui_state.get("shadow_size", 2))
                        border_style_input = gr.Dropdown(choices=[(i18n("Outline"), 1), (i18n("Opaque Box"), 3)], label=i18n("Border Style"), value=ui_state.get("border_s", 1))
                    
                    with gr.Row():
                        bold_input = gr.Checkbox(label=i18n("Bold"), value=ui_state.get("is_bold", False))
                        italic_input = gr.Checkbox(label=i18n("Italic"), value=ui_state.get("is_italic", False))
                        uppercase_input = gr.Checkbox(label=i18n("Uppercase"), value=ui_state.get("is_uppercase", False))
                        remove_punc_input = gr.Checkbox(label=i18n("Remove Punctuation"), value=ui_state.get("remove_punc", True))
                        underline_input = gr.Checkbox(label=i18n("Underline"), value=ui_state.get("under", False))
                        strikeout_input = gr.Checkbox(label=i18n("Strikeout"), value=ui_state.get("strike", False))
                        
                    gr.Markdown(f"### {i18n('Positioning & Layout')}")
                    with gr.Row():
                        vertical_pos_input = gr.Slider(label=i18n("V-Pos (Margin V)"), minimum=0, maximum=500, value=ui_state.get("vertical_pos", 210))
                        alignment_input = gr.Dropdown(choices=[(i18n("Left"), 1), (i18n("Center"), 2), (i18n("Right"), 3)], label=i18n("Alignment"), value=ui_state.get("alignment", 2))
                        gap_limit_input = gr.Slider(label=i18n("Gap Limit"), minimum=0.0, maximum=5.0, value=ui_state.get("gap", 0.5), step=0.1)
                        mode_input = gr.Dropdown(choices=[(i18n("Highlight"), "highlight"), (i18n("Word by Word"), "word_by_word"), (i18n("No Highlight"), "no_highlight")], label=i18n("Mode"), value=ui_state.get("mode", "highlight"))
                        words_per_block_input = gr.Slider(label=i18n("Words per Block"), minimum=1, maximum=20, value=ui_state.get("w_block", 3), step=1)

                manual_inputs = [
                    font_name_input, font_size_input, font_color_input, highlight_color_input, 
                    outline_color_input, outline_thickness_input, shadow_color_input, shadow_size_input, 
                    bold_input, italic_input, uppercase_input,
                    highlight_size_input, words_per_block_input, gap_limit_input, mode_input,
                    underline_input, strikeout_input, border_style_input,
                    vertical_pos_input, alignment_input,
                    remove_punc_input
                ]
                
                # Update manual inputs when preset changes
                preset_input.change(subs.apply_preset, inputs=[preset_input], outputs=manual_inputs)
                
                # Auto-update PREVIEW HTML on any change
                for inp in manual_inputs:
                    inp.change(subs.generate_preview_html, inputs=manual_inputs, outputs=preview_html)
                
                # Render video button
                preview_vid_btn.click(
                    subs.render_preview_video,
                    inputs=manual_inputs,
                    outputs=preview_vid
                )
                
                # Initial load
                demo.load(subs.generate_preview_html, inputs=manual_inputs, outputs=preview_html)

             def restore_saved_toggles():
                 saved = ui_cfg.load_ui_state()
                 def flag(key, default=False):
                     return bool(saved.get(key, default))
                 return (
                     flag("use_youtube_subs", True),
                     flag("viral", True),
                     flag("text_safe_selection", False),
                     flag("enable_captions", True),
                     flag("focus_active_speaker", False),
                     flag("include_motion", False),
                     flag("use_custom_subs", True),
                     flag("is_bold", False),
                     flag("is_italic", False),
                     flag("is_uppercase", False),
                     flag("remove_punc", True),
                     flag("under", False),
                     flag("strike", False),
                 )

             demo.load(
                 restore_saved_toggles,
                 outputs=[
                     use_youtube_subs_input,
                     viral_input,
                     text_safe_selection_input,
                     enable_captions_input,
                     focus_active_speaker_input,
                     include_motion_input,
                     use_custom_subs,
                     bold_input,
                     italic_input,
                     uppercase_input,
                     remove_punc_input,
                     underline_input,
                     strikeout_input,
                 ],
                 queue=False,
                 show_progress="hidden",
             )

             _persist_inputs = [
                 input_source, video_quality_input, translate_input, use_youtube_subs_input,
                 segments_input, viral_input, themes_input, min_dur_input, max_dur_input,
                 text_safe_selection_input, max_text_frame_percent_input,
                 generation_profile_input,
                 ai_backend_input, ai_model_input, chunk_size_input,
                 model_input, enable_captions_input, workflow_input,
                 face_model_input, face_mode_input, face_detect_interval_input, no_face_mode_input,
                 face_preset_input, face_filter_thresh_input, face_two_thresh_input, face_conf_thresh_input, face_dead_zone_input,
                 experimental_preset_input, focus_active_speaker_input, active_speaker_mar_input, active_speaker_score_diff_input,
                 include_motion_input, active_speaker_motion_threshold_input, active_speaker_motion_sensitivity_input, active_speaker_decay_input,
                 preset_input, use_custom_subs,
             ] + manual_inputs

             def _persist_web_settings(api_key, *values):
                 ui_cfg.persist_create_tab_settings(api_key, *values)

             gr.on(
                 triggers=[c.change for c in _persist_inputs],
                 fn=_persist_web_settings,
                 inputs=[api_key_input] + _persist_inputs,
                 outputs=None,
                 queue=False,
                 show_progress="hidden",
             )
             api_key_input.change(
                 lambda backend, key: ui_cfg.save_api_key(backend, key),
                 inputs=[ai_backend_input, api_key_input],
                 outputs=None,
                 queue=False,
                 show_progress="hidden",
             )

             gr.HTML("""
<div class="vc-section-divider vc-output-divider"><span>03</span><div><strong>Output</strong><small>Start processing and follow the render in real time.</small></div></div>
""")
             with gr.Group(elem_classes=["vc-card", "vc-generate-card"]):
                 gr.Markdown(f"### {i18n('Generate')}")
                 with gr.Row():
                     start_btn = gr.Button(i18n("Start Processing"), variant="primary")
                     stop_btn = gr.Button(i18n("Stop"), variant="stop", visible=False)
                 stop_btn.click(kill_process, outputs=[])
                 logs_output = gr.Textbox(label=i18n("Logs"), lines=10, autoscroll=True, elem_id="logs_output")
                 results_html = gr.HTML(label=i18n("Results"))

             # Force scroll to bottom via JS
             logs_output.change(fn=None, inputs=[], outputs=[], js="""
                function() {
                    var ta = document.querySelector('#logs_output textarea');
                    if(ta) {
                        // Setup scroll listener once to track user intent
                        if (!ta._scrollerSetup) {
                            ta._isSticky = true; // Default to sticky
                            ta.addEventListener('scroll', function() {
                                var diff = ta.scrollHeight - ta.scrollTop - ta.clientHeight;
                                // If near bottom (<50px), enable sticky. Else disable.
                                if (diff <= 50) {
                                     ta._isSticky = true;
                                } else {
                                     ta._isSticky = false;
                                }
                            });
                            ta._scrollerSetup = true;
                        }
                        
                        // Apply scroll only if sticky
                        if(ta._isSticky === undefined || ta._isSticky === true) {
                            ta.scrollTop = ta.scrollHeight;
                        }
                    }
                }
             """)

             # MUST pass all all new inputs to the run function
             start_btn.click(run_viral_cutter, inputs=[
                 input_source, project_selector, url_input, video_upload, segments_input, viral_input, themes_input, min_dur_input, max_dur_input, text_safe_selection_input, max_text_frame_percent_input, generation_profile_input,
                 model_input, ai_backend_input, api_key_input, ai_model_input, chunk_size_input, 
                 workflow_input, face_model_input, face_mode_input, face_detect_interval_input, no_face_mode_input, 
                 face_filter_thresh_input, face_two_thresh_input, face_conf_thresh_input, face_dead_zone_input, focus_active_speaker_input, 
                 active_speaker_mar_input, active_speaker_score_diff_input, include_motion_input, active_speaker_motion_threshold_input, active_speaker_motion_sensitivity_input, active_speaker_decay_input,
                 enable_captions_input, use_custom_subs, 
                 # Expanded Manual Inputs mapping
                 font_name_input, font_size_input, font_color_input, highlight_color_input, 
                 outline_color_input, outline_thickness_input, shadow_color_input, shadow_size_input, 
                 bold_input, italic_input, uppercase_input, vertical_pos_input, alignment_input,
                 # New Inputs
                 highlight_size_input, words_per_block_input, gap_limit_input, mode_input, 
                 underline_input, strikeout_input, border_style_input, remove_punc_input,
                 video_quality_input, use_youtube_subs_input, translate_input,
                 face_preset_input, experimental_preset_input, preset_input,
             ], outputs=[logs_output, start_btn, stop_btn, results_html])


        with gr.Tab(i18n("Subtitle Editor"), id="editor"):
            with gr.Group(elem_classes=["vc-card"]):
                gr.Markdown(f"### {i18n('Project')}")
                with gr.Row():
                    editor_project_dropdown = gr.Dropdown(choices=library.get_existing_projects(), label=i18n("Select Project"), value=ui_state.get("editor_project"), scale=4)
                    editor_refresh_btn = gr.Button(i18n("Refresh"), size="sm", scale=1)
                with gr.Row():
                    editor_file_dropdown = gr.Dropdown(choices=[], label=i18n("Select Subtitle File"), interactive=True, scale=4)
                    editor_load_btn = gr.Button(i18n("Load Subtitles"), variant="secondary", scale=1)

            current_json_path = gr.State()

            with gr.Group(elem_classes=["vc-card"]):
                gr.Markdown(f"### {i18n('Segments')}")
                subtitle_dataframe = gr.Dataframe(
                    headers=["Start", "End", "Text"],
                    datatype=["str", "str", "str"],
                    col_count=(3, "fixed"),
                    interactive=True,
                    label=i18n("Subtitle Segments"),
                    wrap=True
                )

            with gr.Group(elem_classes=["vc-card"]):
                gr.Markdown(f"### {i18n('Actions')}")
                with gr.Row():
                    editor_save_btn = gr.Button(i18n("Save Changes"), variant="primary")
                    editor_render_single_btn = gr.Button(i18n("Render This Segment"), variant="secondary")
                    editor_render_all_btn = gr.Button(i18n("Render All"), variant="stop")
                editor_status = gr.Textbox(label=i18n("Status"), interactive=False)

            # --- Callbacks for Editor ---
            editor_refresh_btn.click(library.refresh_projects, outputs=editor_project_dropdown)

            def update_file_list(proj_name):
                if not proj_name: return gr.update(choices=[])
                proj_path = os.path.join(VIRALS_DIR, proj_name)
                files = editor.list_editable_files(proj_path)
                return gr.update(choices=files, value=files[0] if files else None)

            editor_project_dropdown.change(update_file_list, inputs=editor_project_dropdown, outputs=editor_file_dropdown)

            def load_subs(proj_name, file_name):
                if not proj_name or not file_name:
                    return [], None, i18n("Please select project and file.")
                
                full_path = os.path.join(VIRALS_DIR, proj_name, 'subs', file_name)
                data = editor.load_transcription_for_editor(full_path)
                return data, full_path, i18n("Loaded {} segments.").format(len(data))

            editor_load_btn.click(load_subs, inputs=[editor_project_dropdown, editor_file_dropdown], outputs=[subtitle_dataframe, current_json_path, editor_status])

            def save_subs(json_path, df):
                if not json_path: return i18n("No file loaded.")
                data_list = df.values.tolist() if hasattr(df, 'values') else df
                msg = editor.save_editor_changes(json_path, data_list)
                return msg

            editor_save_btn.click(save_subs, inputs=[current_json_path, subtitle_dataframe], outputs=editor_status)

            def render_single(json_path, use_custom, font_name, font_size, font_color, highlight_color, 
                              outline_color, outline_thickness, shadow_color, shadow_size, 
                              is_bold, is_italic, is_uppercase, 
                              h_size, w_block, gap, mode, under, strike, border_s, 
                              vertical_pos, alignment, remove_punc):
                
                if not json_path: return i18n("No file loaded.")
                
                subtitle_config_path = os.path.join(WORKING_DIR, "temp_subtitle_config.json")
                
                # Save config if custom subs enabled
                if use_custom:
                    subtitle_config = {
                        "font": font_name, "base_size": int(font_size), 
                        "base_color": convert_color_to_ass(font_color), 
                        "highlight_color": convert_color_to_ass(highlight_color),
                        "outline_color": convert_color_to_ass(outline_color), 
                        "outline_thickness": outline_thickness, 
                        "shadow_color": convert_color_to_ass(shadow_color),
                        "shadow_size": shadow_size, "vertical_position": vertical_pos, 
                        "alignment": alignment, "bold": 1 if is_bold else 0, 
                        "italic": 1 if is_italic else 0, 
                        "underline": 1 if under else 0, "strikeout": 1 if strike else 0, 
                        "border_style": border_s, "words_per_block": int(w_block), 
                        "gap_limit": gap, "mode": mode, "highlight_size": int(h_size),
                        "uppercase": 1 if is_uppercase else 0,
                        "remove_punctuation": remove_punc
                    }
                    try:
                        with open(subtitle_config_path, "w", encoding="utf-8") as f:
                            json.dump(subtitle_config, f, indent=4)
                    except Exception: pass
                else:
                    # Remove temp config if it exists to ensure defaults are used
                    try:
                        if os.path.exists(subtitle_config_path):
                            os.remove(subtitle_config_path)
                    except Exception: pass
                
                # We expect user to SAVE first, but we could auto-save.
                # For now assume saved.
                msg = editor.render_specific_video(json_path)
                return msg

            editor_render_single_btn.click(
                render_single, 
                inputs=[current_json_path, use_custom_subs] + manual_inputs, 
                outputs=editor_status
            )

            def render_all(proj_name, use_custom, font_name, font_size, font_color, highlight_color, 
                           outline_color, outline_thickness, shadow_color, shadow_size, 
                           is_bold, is_italic, is_uppercase, 
                           h_size, w_block, gap, mode, under, strike, border_s, 
                           vertical_pos, alignment, remove_punc):
                if not proj_name: return i18n("No project selected.")
                
                # Save config
                if use_custom:
                    subtitle_config = {
                        "font": font_name, "base_size": int(font_size), 
                        "base_color": convert_color_to_ass(font_color), 
                        "highlight_color": convert_color_to_ass(highlight_color),
                        "outline_color": convert_color_to_ass(outline_color), 
                        "outline_thickness": outline_thickness, 
                        "shadow_color": convert_color_to_ass(shadow_color),
                        "shadow_size": shadow_size, "vertical_position": vertical_pos, 
                        "alignment": alignment, "bold": 1 if is_bold else 0, 
                        "italic": 1 if is_italic else 0, 
                        "underline": 1 if under else 0, "strikeout": 1 if strike else 0, 
                        "border_style": border_s, "words_per_block": int(w_block), 
                        "gap_limit": gap, "mode": mode, "highlight_size": int(h_size),
                        "uppercase": 1 if is_uppercase else 0,
                        "remove_punctuation": remove_punc
                    }
                    subtitle_config_path = os.path.join(WORKING_DIR, "temp_subtitle_config.json")
                    try:
                        with open(subtitle_config_path, "w", encoding="utf-8") as f:
                            json.dump(subtitle_config, f, indent=4)
                    except Exception: pass

                proj_path = os.path.join(VIRALS_DIR, proj_name)
                
                # IMPORTANT: Pass the config file path to the command
                subtitle_config_path = os.path.join(WORKING_DIR, "temp_subtitle_config.json")
                cmd = [sys.executable, MAIN_SCRIPT_PATH, "--project-path", proj_path, "--workflow", "3", "--skip-prompts"]
                
                if use_custom and os.path.exists(subtitle_config_path):
                     cmd.extend(["--subtitle-config", subtitle_config_path])

                try:
                    subprocess.Popen(cmd, cwd=WORKING_DIR)
                    return i18n("Render All started in background... Check terminal/logs.")
                except Exception as e:
                    return i18n("Error starting render: {}").format(e)

            editor_render_all_btn.click(
                render_all, 
                inputs=[editor_project_dropdown, use_custom_subs] + manual_inputs, 
                outputs=editor_status
            )

            editor_project_dropdown.change(
                lambda project: ui_cfg.save_ui_state({"editor_project": project}),
                inputs=editor_project_dropdown,
                outputs=None,
                queue=False,
                show_progress="hidden",
            )


        with gr.Tab(i18n("Library"), id="library"):
            with gr.Group(elem_classes=["vc-card"]):
                gr.Markdown(f"### {i18n('Projects')}")
                with gr.Row():
                    project_dropdown = gr.Dropdown(choices=library.get_existing_projects(), label=i18n("Select Project"), value=ui_state.get("library_project"), scale=4)
                    refresh_btn = gr.Button(i18n("Refresh List"), scale=1)
            with gr.Group(elem_classes=["vc-card"]):
                gr.Markdown(f"### {i18n('Gallery')}")
                project_gallery_html = gr.HTML()
            refresh_btn.click(library.refresh_projects, outputs=project_dropdown)
            def on_select_project(proj_name): return library.generate_project_gallery(proj_name)
            project_dropdown.change(on_select_project, project_dropdown, project_gallery_html)
            project_dropdown.change(
                lambda project: ui_cfg.save_ui_state({"library_project": project}),
                inputs=project_dropdown,
                outputs=None,
                queue=False,
                show_progress="hidden",
            )
            if ui_state.get("library_project"):
                demo.load(on_select_project, inputs=project_dropdown, outputs=project_gallery_html, queue=False, show_progress="hidden")

    def select_workspace_tab(tab_id):
        return gr.Tabs(selected=tab_id)

    def workspace_nav_js(tab_index):
        return f"""
() => {{
  const navButtons = Array.from(document.querySelectorAll('#vc-workspace-nav button'));
  navButtons.forEach((button, index) => button.classList.toggle('vc-nav-active', index === {tab_index}));
}}
"""

    nav_create_btn.click(
        fn=lambda: select_workspace_tab("create"),
        outputs=main_tabs,
        js=workspace_nav_js(0),
        queue=False,
        show_progress="hidden",
    )
    nav_editor_btn.click(
        fn=lambda: select_workspace_tab("editor"),
        outputs=main_tabs,
        js=workspace_nav_js(1),
        queue=False,
        show_progress="hidden",
    )
    nav_library_btn.click(
        fn=lambda: select_workspace_tab("library"),
        outputs=main_tabs,
        js=workspace_nav_js(2),
        queue=False,
        show_progress="hidden",
    )
    
    gr.Markdown("""
        <div class="vc-footer">
            100% local · open source · no subscription required
        </div>
        """)
if __name__ == "__main__":
    import webbrowser
    import threading
    import time
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--colab", action="store_true", help="Run in Google Colab mode")
    args = parser.parse_args()

    if args.colab:
        print("Running in Colab mode. Generating public link with Static Mounts...")
        library.set_url_mode("fastapi")
        
        # Broaden allowed paths for Colab
        allowed_dirs = [VIRALS_DIR, WORKING_DIR, os.getcwd(), "."]
        
        # Explicitly set static paths
        try:
            gr.set_static_paths(paths=allowed_dirs)
            print(f"DEBUG: Registered static paths: {allowed_dirs}")
        except AttributeError:
            print("DEBUG: gr.set_static_paths not available")
        
        print(f"DEBUG: Allowed paths for Gradio: {allowed_dirs}")
        
        # Launch with prevent_thread_lock to allow mounting
        app, local_url, share_url = demo.queue().launch(
            share=True, 
            allowed_paths=allowed_dirs,
            prevent_thread_lock=True
        )
        
        # Mount the VIRALS directory explicitly
        app.mount("/virals", StaticFiles(directory=VIRALS_DIR), name="virals")
        print(f"Mounted /virals to {VIRALS_DIR}")
        
        demo.block_thread()
    else:
        # Check environment
        is_windows = (os.name == 'nt')
        
        library.set_url_mode("fastapi")
        allowed_dirs = [VIRALS_DIR, WORKING_DIR, os.getcwd(), "."]
        try:
            gr.set_static_paths(paths=allowed_dirs)
        except AttributeError: pass
        
        from fastapi.responses import FileResponse
        from fastapi import BackgroundTasks

        # Helper to attach routes to any FastAPI app (whether created by Gradio or us)
        def attach_extra_routes(fastapi_app):
            fastapi_app.mount("/virals", StaticFiles(directory=VIRALS_DIR), name="virals")
            
            @fastapi_app.get("/export_xml_api")
            def export_xml_api(project: str, segment: int, background_tasks: BackgroundTasks, format: str = "premiere"):
                try:
                    project_path = os.path.join(VIRALS_DIR, project)
                    script_path = os.path.join(WORKING_DIR, "scripts", "export_xml.py")
                    cmd = [sys.executable, script_path, "--project", project_path, "--segment", str(segment), "--format", format]
                    subprocess.run(cmd, check=True)
                    proj_name = os.path.basename(project_path)
                    zip_filename = f"export_{proj_name}_seg{segment}.zip"
                    file_path = os.path.join(project_path, zip_filename)
                    if os.path.exists(file_path):
                        return FileResponse(file_path, filename=zip_filename, media_type='application/zip')
                    else:
                        return {"error": f"File generation failed. Expected: {file_path}"}
                except Exception as e:
                    return {"error": str(e)}
            
            print(f"Mounted /virals to {VIRALS_DIR}")

        if is_windows:
            print("Running in Windows environment (using Gradio launch for convenience).")
            # Windows: Use demo.launch() for convenience (auto-browser, etc)
            app, local_url, share_url = demo.queue().launch(
                share=False, 
                allowed_paths=allowed_dirs, 
                inbrowser=True,
                server_name="0.0.0.0",
                server_port=7860,
                prevent_thread_lock=True,
                theme=vc_theme,
                css=css,
                head=head_script,
                js=theme_init_js,
            )
            attach_extra_routes(app)
            demo.block_thread()
        else:
            print("Running in Linux/Container environment (using Uvicorn for stability).")
            # Linux/HF: Use Uvicorn for explicit loop control
            app = FastAPI()
            attach_extra_routes(app)
            # Disable SSR to prevent Node proxying issues on HF Spaces
            app = gr.mount_gradio_app(
                app,
                demo.queue(),
                path="/",
                allowed_paths=allowed_dirs,
                ssr_mode=False,
                theme=vc_theme,
                css=css,
                head=head_script,
                js=theme_init_js,
            )
            uvicorn.run(app, host="0.0.0.0", port=7860)
