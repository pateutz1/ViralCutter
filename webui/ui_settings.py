import json
import os

WORKING_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_SETTINGS_PATH = os.path.join(WORKING_DIR, "ui_settings.json")
API_CONFIG_PATH = os.path.join(WORKING_DIR, "api_config.json")

DEFAULT_UI_SETTINGS = {
    "input_source": "YouTube URL",
    "video_quality": "best",
    "translate_target": "None",
    "use_youtube_subs": True,
    "segments": 3,
    "viral": True,
    "themes": "",
    "min_duration": 15,
    "max_duration": 90,
    "text_safe_selection": False,
    "max_text_frame_percent": 15,
    "ai_backend": "gemini",
    "ai_model_name": "gemini-3.7-flash",
    "chunk_size": 70000,
    "whisper_backend": "cloudflare",
    "enable_captions": True,
    "workflow": "Full",
    "face_model": "insightface",
    "face_mode": "auto",
    "face_detect_interval": "0.17,1.0",
    "no_face_mode": "zoom",
    "face_preset": "Default (Balanced)",
    "face_filter_thresh": 0.35,
    "face_two_thresh": 0.60,
    "face_conf_thresh": 0.40,
    "face_dead_zone": 150,
    "experimental_preset": "Default (Off)",
    "focus_active_speaker": False,
    "active_speaker_mar": 0.03,
    "active_speaker_score_diff": 1.5,
    "include_motion": False,
    "active_speaker_motion_threshold": 3.0,
    "active_speaker_motion_sensitivity": 0.05,
    "active_speaker_decay": 2.0,
    "subtitle_preset": "Hormozi (Classic)",
    "use_custom_subs": True,
    "font_name": "Montserrat-Regular",
    "font_size": 12,
    "highlight_size": 14,
    "font_color": "#FFFFFF",
    "highlight_color": "#00FF00",
    "outline_color": "#000000",
    "shadow_color": "#000000",
    "outline_thickness": 1.5,
    "shadow_size": 2,
    "border_s": 1,
    "is_bold": False,
    "is_italic": False,
    "is_uppercase": False,
    "remove_punc": True,
    "under": False,
    "strike": False,
    "vertical_pos": 210,
    "alignment": 2,
    "gap": 0.5,
    "mode": "highlight",
    "w_block": 3,
    "editor_project": None,
    "library_project": None,
    "theme": "dark",
}


def load_api_config():
    if not os.path.exists(API_CONFIG_PATH):
        return {}
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_ui_state():
    state = dict(DEFAULT_UI_SETTINGS)
    if os.path.exists(UI_SETTINGS_PATH):
        try:
            with open(UI_SETTINGS_PATH, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                state.update(loaded)
        except Exception:
            pass
    return state


def save_ui_state(data):
    merged = load_ui_state()
    merged.update(data or {})
    try:
        with open(UI_SETTINGS_PATH, "w", encoding="utf-8") as handle:
            json.dump(merged, handle, indent=4)
    except Exception:
        pass


def load_saved_api_key(backend):
    backend = (backend or "").strip().lower()
    cfg = load_api_config()
    if backend == "gemini":
        return (cfg.get("gemini") or {}).get("api_key", "") or ""
    if backend == "groq":
        return (cfg.get("groq") or {}).get("api_key", "") or ""
    return ""


def save_api_key(backend, key):
    backend = (backend or "").strip().lower()
    key = (key or "").strip()
    if not key or backend not in ("gemini", "groq"):
        return

    cfg = load_api_config()
    cfg["selected_api"] = backend
    cfg.setdefault(backend, {})["api_key"] = key
    try:
        with open(API_CONFIG_PATH, "w", encoding="utf-8") as handle:
            json.dump(cfg, handle, indent=4)
    except Exception:
        pass


def settings_from_create_tab(
    input_source,
    video_quality,
    translate_target,
    use_youtube_subs,
    segments,
    viral,
    themes,
    min_duration,
    max_duration,
    text_safe_selection,
    max_text_frame_percent,
    ai_backend,
    ai_model_name,
    chunk_size,
    whisper_backend,
    enable_captions,
    workflow,
    face_model,
    face_mode,
    face_detect_interval,
    no_face_mode,
    face_preset,
    face_filter_thresh,
    face_two_thresh,
    face_conf_thresh,
    face_dead_zone,
    experimental_preset,
    focus_active_speaker,
    active_speaker_mar,
    active_speaker_score_diff,
    include_motion,
    active_speaker_motion_threshold,
    active_speaker_motion_sensitivity,
    active_speaker_decay,
    subtitle_preset,
    use_custom_subs,
    font_name,
    font_size,
    font_color,
    highlight_color,
    outline_color,
    outline_thickness,
    shadow_color,
    shadow_size,
    is_bold,
    is_italic,
    is_uppercase,
    highlight_size,
    w_block,
    gap,
    mode,
    under,
    strike,
    border_s,
    vertical_pos,
    alignment,
    remove_punc,
):
    return {
        "input_source": input_source,
        "video_quality": video_quality,
        "translate_target": translate_target,
        "use_youtube_subs": use_youtube_subs,
        "segments": segments,
        "viral": viral,
        "themes": themes or "",
        "min_duration": min_duration,
        "max_duration": max_duration,
        "text_safe_selection": text_safe_selection,
        "max_text_frame_percent": max_text_frame_percent,
        "ai_backend": ai_backend,
        "ai_model_name": ai_model_name,
        "chunk_size": chunk_size,
        "whisper_backend": whisper_backend,
        "enable_captions": enable_captions,
        "workflow": workflow,
        "face_model": face_model,
        "face_mode": face_mode,
        "face_detect_interval": face_detect_interval,
        "no_face_mode": no_face_mode,
        "face_preset": face_preset,
        "face_filter_thresh": face_filter_thresh,
        "face_two_thresh": face_two_thresh,
        "face_conf_thresh": face_conf_thresh,
        "face_dead_zone": face_dead_zone,
        "experimental_preset": experimental_preset,
        "focus_active_speaker": focus_active_speaker,
        "active_speaker_mar": active_speaker_mar,
        "active_speaker_score_diff": active_speaker_score_diff,
        "include_motion": include_motion,
        "active_speaker_motion_threshold": active_speaker_motion_threshold,
        "active_speaker_motion_sensitivity": active_speaker_motion_sensitivity,
        "active_speaker_decay": active_speaker_decay,
        "subtitle_preset": subtitle_preset,
        "use_custom_subs": use_custom_subs,
        "font_name": font_name,
        "font_size": font_size,
        "font_color": font_color,
        "highlight_color": highlight_color,
        "outline_color": outline_color,
        "outline_thickness": outline_thickness,
        "shadow_color": shadow_color,
        "shadow_size": shadow_size,
        "is_bold": is_bold,
        "is_italic": is_italic,
        "is_uppercase": is_uppercase,
        "highlight_size": highlight_size,
        "w_block": w_block,
        "gap": gap,
        "mode": mode,
        "under": under,
        "strike": strike,
        "border_s": border_s,
        "vertical_pos": vertical_pos,
        "alignment": alignment,
        "remove_punc": remove_punc,
    }


def persist_create_tab_settings(api_key, *create_tab_values):
    payload = settings_from_create_tab(*create_tab_values)
    save_ui_state(payload)
    save_api_key(payload.get("ai_backend"), api_key)
