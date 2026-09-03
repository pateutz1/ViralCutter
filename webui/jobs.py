import datetime
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time

import library
import psutil
import ui_settings as ui_cfg

WORKING_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_SCRIPT_PATH = os.path.join(WORKING_DIR, "main_improved.py")
VIRALS_DIR = os.path.join(WORKING_DIR, "VIRALS")

sys.path.append(WORKING_DIR)

from i18n.i18n import I18nAuto
i18n = I18nAuto()

GEMINI_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
]

G4F_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4",
    "o1-mini",
    "o1",
    "deepseek-r1",
    "deepseek-v3",
    "llama-3.3-70b",
    "llama-3.1-405b",
    "claude-3.5-sonnet",
    "claude-3.7-sonnet",
    "gemini-2.0-flash",
    "qwen-2.5-72b",
]

GROQ_MODELS = ["openai/gpt-oss-120b"]
CLOUDFLARE_MODELS = ["@cf/openai/gpt-oss-120b"]
WHISPER_BACKENDS = ["cloudflare", "groq", "azure"]

EXPERIMENTAL_PRESETS = {
    "Default (Off)": {"focus": False, "mar": 0.03, "score": 1.5, "motion": False, "motion_th": 3.0, "motion_sens": 0.05, "decay": 2.0},
    "Active Speaker (Balanced)": {"focus": True, "mar": 0.03, "score": 1.5, "motion": True, "motion_th": 3.0, "motion_sens": 0.05, "decay": 2.0},
    "Active Speaker (Sensitive)": {"focus": True, "mar": 0.02, "score": 1.0, "motion": True, "motion_th": 2.0, "motion_sens": 0.10, "decay": 1.0},
    "Active Speaker (Stable)": {"focus": True, "mar": 0.05, "score": 2.5, "motion": False, "motion_th": 5.0, "motion_sens": 0.02, "decay": 3.0},
}

current_process = None
_job_lock = threading.Lock()
_active_job = None


class Job:
    def __init__(self, job_id):
        self.job_id = job_id
        self.events = queue.Queue()
        self.logs = ""
        self.running = True
        self.gallery_html = ""
        self.error = None

    def push(self, logs=None, gallery=None, done=False, error=None):
        if logs is not None:
            self.logs = logs
        if gallery is not None:
            self.gallery_html = gallery
        if error is not None:
            self.error = error
        if done:
            self.running = False
        self.events.put({
            "logs": self.logs,
            "running": self.running,
            "gallery_html": self.gallery_html,
            "error": self.error,
            "done": done,
        })


def convert_color_to_ass(hex_color, alpha="00"):
    import re
    if not hex_color:
        return f"&H{alpha}FFFFFF&"
    hex_clean = hex_color.lstrip("#").strip()
    if hex_clean.lower().startswith("rgb"):
        try:
            values = re.findall(r"[\d.]+", hex_clean)
            if len(values) >= 3:
                red, green, blue = (max(0, min(255, int(float(value)))) for value in values[:3])
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


def models_for_backend(backend):
    if backend == "gemini":
        return list(GEMINI_MODELS)
    if backend == "g4f":
        return list(G4F_MODELS)
    if backend == "groq":
        return list(GROQ_MODELS)
    if backend == "cloudflare":
        return list(CLOUDFLARE_MODELS)
    return []


def default_chunk_for(backend, model_name, saved_chunk=70000):
    if backend in ("groq", "cloudflare"):
        return 40000
    if model_name and "pro" in str(model_name).lower() and "flash" not in str(model_name).lower():
        return 20000
    return saved_chunk or 70000


def write_subtitle_config(payload):
    if not payload.get("use_custom_subs"):
        return None
    subtitle_config = {
        "font": payload.get("font_name"),
        "base_size": int(payload.get("font_size") or 12),
        "base_color": convert_color_to_ass(payload.get("font_color")),
        "highlight_color": convert_color_to_ass(payload.get("highlight_color")),
        "outline_color": convert_color_to_ass(payload.get("outline_color")),
        "outline_thickness": payload.get("outline_thickness"),
        "shadow_color": convert_color_to_ass(payload.get("shadow_color")),
        "shadow_size": payload.get("shadow_size"),
        "vertical_position": payload.get("vertical_pos"),
        "alignment": payload.get("alignment"),
        "bold": 1 if payload.get("is_bold") else 0,
        "italic": 1 if payload.get("is_italic") else 0,
        "underline": 1 if payload.get("under") else 0,
        "strikeout": 1 if payload.get("strike") else 0,
        "border_style": payload.get("border_s"),
        "words_per_block": int(payload.get("w_block") or 3),
        "gap_limit": payload.get("gap"),
        "mode": payload.get("mode"),
        "highlight_size": int(payload.get("highlight_size") or 14),
        "remove_punctuation": payload.get("remove_punc"),
        "uppercase": 1 if payload.get("is_uppercase") else 0,
    }
    subtitle_config_path = os.path.join(WORKING_DIR, "temp_subtitle_config.json")
    with open(subtitle_config_path, "w", encoding="utf-8") as handle:
        json.dump(subtitle_config, handle, indent=4)
    return subtitle_config_path


def persist_payload(payload):
    api_key = payload.get("api_key")
    data = {key: payload.get(key) for key in ui_cfg.DEFAULT_UI_SETTINGS if key in payload}
    ui_cfg.save_ui_state(data)
    ui_cfg.save_api_key(payload.get("ai_backend"), api_key)


def run_viral_cutter(payload, job):
    global current_process
    persist_payload(payload)
    job.push(logs="")

    cmd = [sys.executable, MAIN_SCRIPT_PATH]
    input_source = payload.get("input_source") or "YouTube URL"
    project_name = payload.get("project_name")
    url = payload.get("url")
    video_file = payload.get("video_file")

    if input_source == "Existing Project":
        if not project_name:
            job.push(logs=i18n("Error: No project selected."), done=True, error="No project selected.")
            return
        cmd.extend(["--project-path", os.path.join(VIRALS_DIR, project_name)])
    elif input_source == "Upload Video":
        if not video_file:
            job.push(logs=i18n("Error: No video file uploaded."), done=True, error="No video file uploaded.")
            return
        original_filename = os.path.basename(video_file)
        name_no_ext = os.path.splitext(original_filename)[0]
        safe_name = "".join([c for c in name_no_ext if c.isalnum() or c in " _-"]).strip() or "Untitled_Upload"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name_upload = f"{safe_name}_{timestamp}"
        project_path = os.path.join(VIRALS_DIR, project_name_upload)
        os.makedirs(project_path, exist_ok=True)
        shutil.copy(video_file, os.path.join(project_path, "input.mp4"))
        cmd.extend(["--project-path", project_path])
        cmd.append("--skip-youtube-subs")
    else:
        if url:
            cmd.extend(["--url", url])
        if payload.get("video_quality"):
            cmd.extend(["--video-quality", payload.get("video_quality")])
        if not payload.get("use_youtube_subs"):
            cmd.append("--skip-youtube-subs")

    translate_target = payload.get("translate_target")
    if translate_target and translate_target != "None":
        cmd.extend(["--translate-target", translate_target])

    cmd.extend(["--segments", str(int(payload.get("segments") or 3))])
    if payload.get("viral"):
        cmd.append("--viral")
    if payload.get("themes"):
        cmd.extend(["--themes", payload.get("themes")])
    cmd.extend(["--min-duration", str(int(payload.get("min_duration") or 15))])
    cmd.extend(["--max-duration", str(int(payload.get("max_duration") or 90))])
    if payload.get("text_safe_selection"):
        cmd.append("--text-safe-selection")
        cmd.extend(["--max-text-frame-percent", str(float(payload.get("max_text_frame_percent") or 15))])
    cmd.extend(["--model", payload.get("whisper_backend") or payload.get("model") or "cloudflare"])
    cmd.extend(["--ai-backend", payload.get("ai_backend") or "gemini"])
    if payload.get("api_key"):
        cmd.extend(["--api-key", payload.get("api_key")])
    if not payload.get("enable_captions", True):
        cmd.append("--no-subtitles")
        cmd.append("--skip-youtube-subs")
    if payload.get("ai_model_name"):
        cmd.extend(["--ai-model-name", str(payload.get("ai_model_name"))])
    if payload.get("chunk_size"):
        cmd.extend(["--chunk-size", str(int(payload.get("chunk_size")))])

    workflow_map = {"Full": "1", "Cut Only": "2", "Subtitles Only": "3"}
    cmd.extend(["--workflow", workflow_map.get(payload.get("workflow"), "1")])
    cmd.extend(["--face-model", payload.get("face_model") or "insightface"])
    cmd.extend(["--face-mode", payload.get("face_mode") or "auto"])
    if payload.get("face_detect_interval"):
        cmd.extend(["--face-detect-interval", str(payload.get("face_detect_interval"))])
    if payload.get("no_face_mode"):
        cmd.extend(["--no-face-mode", payload.get("no_face_mode")])
    if payload.get("face_filter_thresh") is not None:
        cmd.extend(["--face-filter-threshold", str(payload.get("face_filter_thresh"))])
    if payload.get("face_two_thresh") is not None:
        cmd.extend(["--face-two-threshold", str(payload.get("face_two_thresh"))])
    if payload.get("face_conf_thresh") is not None:
        cmd.extend(["--face-confidence-threshold", str(payload.get("face_conf_thresh"))])
    if payload.get("face_dead_zone") is not None:
        cmd.extend(["--face-dead-zone", str(payload.get("face_dead_zone"))])

    cmd.append("--skip-prompts")
    if payload.get("focus_active_speaker"):
        cmd.append("--focus-active-speaker")
        if payload.get("active_speaker_mar") is not None:
            cmd.extend(["--active-speaker-mar", str(payload.get("active_speaker_mar"))])
        if payload.get("active_speaker_score_diff") is not None:
            cmd.extend(["--active-speaker-score-diff", str(payload.get("active_speaker_score_diff"))])
        if payload.get("include_motion"):
            cmd.append("--include-motion")
        if payload.get("active_speaker_motion_threshold") is not None:
            cmd.extend(["--active-speaker-motion-threshold", str(payload.get("active_speaker_motion_threshold"))])
        if payload.get("active_speaker_motion_sensitivity") is not None:
            cmd.extend(["--active-speaker-motion-sensitivity", str(payload.get("active_speaker_motion_sensitivity"))])
        if payload.get("active_speaker_decay") is not None:
            cmd.extend(["--active-speaker-decay", str(payload.get("active_speaker_decay"))])
    cmd.append("--skip-prompts")

    try:
        config_path = write_subtitle_config(payload)
        if config_path:
            cmd.extend(["--subtitle-config", config_path])
    except Exception:
        pass

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    logs = ""
    project_folder_path = None
    if input_source == "Existing Project" and project_name:
        project_folder_path = os.path.join(VIRALS_DIR, project_name)

    try:
        current_process = subprocess.Popen(
            cmd,
            cwd=WORKING_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
        )
        last_update_time = time.time()
        while True:
            line = current_process.stdout.readline()
            if not line and current_process.poll() is not None:
                break
            if line:
                logs += line
                if "Project Folder:" in line:
                    parts = line.split("Project Folder:")
                    if len(parts) > 1:
                        project_folder_path = parts[1].strip()
                current_time = time.time()
                if current_time - last_update_time > 0.2:
                    job.push(logs=logs)
                    last_update_time = current_time
        job.push(logs=logs)
    except Exception as e:
        logs += f"\nError running process: {str(e)}\n"
        job.push(logs=logs, error=str(e))
    finally:
        if current_process:
            if current_process.stdout:
                try:
                    current_process.stdout.close()
                except Exception:
                    pass
            if current_process.poll() is None:
                try:
                    current_process.wait()
                except Exception:
                    pass
            current_process = None

    time.sleep(1.0)
    if project_folder_path and os.path.exists(project_folder_path):
        html_output = library.generate_project_gallery(project_folder_path, is_full_path=True)
    else:
        html_output = f"<h3>{i18n('Error: Project folder could not be determined from logs.')}</h3>"
    job.push(logs=logs, gallery=html_output, done=True)


def start_job(payload):
    global _active_job
    with _job_lock:
        if _active_job and _active_job.running:
            raise RuntimeError("A job is already running.")
        job = Job(str(int(time.time() * 1000)))
        _active_job = job
    thread = threading.Thread(target=run_viral_cutter, args=(payload, job), daemon=True)
    thread.start()
    return job


def get_job(job_id=None):
    if job_id and _active_job and _active_job.job_id != job_id:
        return None
    return _active_job
