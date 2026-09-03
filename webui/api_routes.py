import os
import subprocess
import sys
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import generation_profiles
import jobs
import library
import subtitle_editor as editor
import subtitle_handler as subs
import ui_settings as ui_cfg

WORKING_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIRALS_DIR = os.path.join(WORKING_DIR, "VIRALS")
PREVIEW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PREVIEW")
UPLOAD_DIR = os.path.join(WORKING_DIR, "uploads")
MAIN_SCRIPT_PATH = os.path.join(WORKING_DIR, "main_improved.py")

router = APIRouter()


class SettingsPayload(BaseModel):
    data: dict = {}


class ApiKeyPayload(BaseModel):
    backend: str
    key: str = ""


class PresetPayload(BaseModel):
    name: str = ""


class EditorSavePayload(BaseModel):
    path: str
    rows: list = []


class EditorRenderPayload(BaseModel):
    path: str = ""
    project: str = ""
    settings: dict = {}


class RunPayload(BaseModel):
    settings: dict = {}


def _subtitle_style_args(data):
    return (
        data.get("font_name", "Montserrat-Regular"),
        data.get("font_size", 12),
        data.get("font_color", "#FFFFFF"),
        data.get("highlight_color", "#00FF00"),
        data.get("outline_color", "#000000"),
        data.get("outline_thickness", 1.5),
        data.get("shadow_color", "#000000"),
        data.get("shadow_size", 2),
        data.get("is_bold", False),
        data.get("is_italic", False),
        data.get("is_uppercase", False),
        data.get("highlight_size", 14),
        data.get("w_block", 3),
        data.get("gap", 0.5),
        data.get("mode", "highlight"),
        data.get("under", False),
        data.get("strike", False),
        data.get("border_s", 1),
        data.get("vertical_pos", 210),
        data.get("alignment", 2),
        data.get("remove_punc", True),
    )


def _map_subtitle_preset(preset_name):
    raw = subs.SUBTITLE_PRESETS.get(preset_name)
    if not raw:
        return None
    return {
        "font_name": raw["font_name"],
        "font_size": raw["font_size"],
        "font_color": raw["base_color"],
        "highlight_color": raw["highlight_color"],
        "outline_color": raw["outline_color"],
        "outline_thickness": raw["outline_thickness"],
        "shadow_color": raw["shadow_color"],
        "shadow_size": raw["shadow_size"],
        "is_bold": raw["bold"],
        "is_italic": raw["italic"],
        "is_uppercase": raw["uppercase"],
        "highlight_size": raw["highlight_size"],
        "w_block": raw["words_per_block"],
        "gap": raw["gap_limit"],
        "mode": raw["mode"],
        "under": raw["underline"],
        "strike": raw["strikeout"],
        "border_s": raw["border_style"],
        "vertical_pos": raw.get("vertical_position", 210),
        "alignment": raw.get("alignment", 2),
        "remove_punc": raw.get("remove_punctuation", True),
    }


@router.get("/api/ui-state")
def get_ui_state():
    state = ui_cfg.load_ui_state()
    backend = state.get("ai_backend", "gemini")
    return {
        "state": state,
        "api_key": ui_cfg.load_saved_api_key(backend),
        "options": {
            "projects": library.get_existing_projects(),
            "generation_profiles": list(generation_profiles.GENERATION_PROFILES.keys()),
            "face_presets": list(generation_profiles.FACE_PRESETS.keys()),
            "experimental_presets": list(jobs.EXPERIMENTAL_PRESETS.keys()),
            "subtitle_presets": ["Manual"] + list(subs.SUBTITLE_PRESETS.keys()),
            "ai_backends": ["gemini", "groq", "cloudflare", "g4f", "manual"],
            "models": {
                "gemini": jobs.GEMINI_MODELS,
                "g4f": jobs.G4F_MODELS,
                "groq": jobs.GROQ_MODELS,
                "cloudflare": jobs.CLOUDFLARE_MODELS,
                "manual": [],
            },
            "whisper_backends": jobs.WHISPER_BACKENDS,
        },
    }


@router.post("/api/settings")
def save_settings(payload: SettingsPayload):
    incoming = dict(payload.data or {})
    api_key = incoming.pop("api_key", None)
    data = {key: incoming[key] for key in ui_cfg.DEFAULT_UI_SETTINGS if key in incoming}
    ui_cfg.save_ui_state(data)
    if api_key is not None:
        ui_cfg.save_api_key(data.get("ai_backend") or incoming.get("ai_backend"), api_key)
    return {"ok": True}


@router.post("/api/api-key")
def save_api_key(payload: ApiKeyPayload):
    ui_cfg.save_api_key(payload.backend, payload.key)
    return {"ok": True, "api_key": ui_cfg.load_saved_api_key(payload.backend)}


@router.get("/api/projects")
def list_projects():
    return {"projects": library.get_existing_projects()}


@router.get("/api/backend/{backend}")
def backend_defaults(backend: str):
    saved = ui_cfg.load_ui_state()
    models = jobs.models_for_backend(backend)
    model = saved.get("ai_model_name", "")
    if models and model not in models:
        model = models[0]
    chunk = jobs.default_chunk_for(backend, model, saved.get("chunk_size", 70000))
    return {
        "models": models,
        "model": model,
        "chunk_size": chunk,
        "show_api_key": backend in ("gemini", "groq"),
        "api_key": ui_cfg.load_saved_api_key(backend),
        "api_label": "Groq API Key" if backend == "groq" else "Gemini API Key",
    }


@router.post("/api/presets/face")
def face_preset(payload: PresetPayload):
    preset = generation_profiles.FACE_PRESETS.get(payload.name)
    if not preset:
        return {}
    return {
        "face_filter_thresh": preset["thresh"],
        "face_two_thresh": preset["two_face"],
        "face_conf_thresh": preset["conf"],
        "face_dead_zone": preset["dead_zone"],
    }


@router.post("/api/presets/generation")
def generation_preset(payload: PresetPayload):
    profile = generation_profiles.resolve_generation_profile(payload.name)
    if not profile:
        return {}
    return {
        "segments": profile["segments"],
        "min_duration": profile["min_duration"],
        "max_duration": profile["max_duration"],
        "face_mode": profile["face_mode"],
        "face_detect_interval": profile["face_detect_interval"],
        "no_face_mode": profile["no_face_mode"],
        "face_preset": profile["face_preset"],
        "face_filter_thresh": profile["thresh"],
        "face_two_thresh": profile["two_face"],
        "face_conf_thresh": profile["conf"],
        "face_dead_zone": profile["dead_zone"],
    }


@router.post("/api/presets/experimental")
def experimental_preset(payload: PresetPayload):
    preset = jobs.EXPERIMENTAL_PRESETS.get(payload.name)
    if not preset:
        return {}
    return {
        "focus_active_speaker": preset["focus"],
        "active_speaker_mar": preset["mar"],
        "active_speaker_score_diff": preset["score"],
        "include_motion": preset["motion"],
        "active_speaker_motion_threshold": preset["motion_th"],
        "active_speaker_motion_sensitivity": preset["motion_sens"],
        "active_speaker_decay": preset["decay"],
    }


@router.post("/api/subtitles/preset")
def subtitle_preset(payload: PresetPayload):
    mapped = _map_subtitle_preset(payload.name)
    return mapped or {}


@router.post("/api/subtitles/preview")
def subtitle_preview(payload: SettingsPayload):
    html = subs.generate_preview_html(*_subtitle_style_args(payload.data or {}))
    return {"html": html}


@router.post("/api/subtitles/preview-video")
def subtitle_preview_video(payload: SettingsPayload):
    path = subs.render_preview_video(*_subtitle_style_args(payload.data or {}))
    if not (isinstance(path, str) and os.path.exists(path)):
        raise HTTPException(status_code=500, detail="Preview render failed.")
    return {"url": f"/preview/{os.path.basename(path)}"}


@router.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    suffix = os.path.splitext(file.filename or "upload.mp4")[1] or ".mp4"
    dest = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{suffix}")
    with open(dest, "wb") as handle:
        handle.write(await file.read())
    return {"path": dest, "filename": file.filename}


@router.post("/api/run")
def start_run(payload: RunPayload):
    try:
        job = jobs.start_job(payload.settings or {})
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"job_id": job.job_id}


@router.get("/api/run/{job_id}/stream")
def stream_run(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    def event_source():
        import json
        while True:
            try:
                event = job.events.get(timeout=15)
            except Exception:
                yield "event: ping\ndata: {}\n\n"
                if not job.running:
                    break
                continue
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("done"):
                break

    return StreamingResponse(event_source(), media_type="text/event-stream")


@router.post("/api/run/stop")
def stop_run():
    return {"message": jobs.kill_process()}


@router.get("/api/gallery/{project}")
def project_gallery(project: str):
    return {"html": library.generate_project_gallery(project)}


@router.get("/api/library/projects")
def library_projects():
    return {"projects": library.get_existing_projects()}


@router.get("/api/library/gallery/{project}")
def library_gallery(project: str):
    ui_cfg.save_ui_state({"library_project": project})
    return {"html": library.generate_project_gallery(project)}


@router.get("/api/editor/files")
def editor_files(project: str = ""):
    if not project:
        return {"files": []}
    files = editor.list_editable_files(os.path.join(VIRALS_DIR, project))
    ui_cfg.save_ui_state({"editor_project": project})
    return {"files": files}


@router.get("/api/editor/load")
def editor_load(project: str = "", file: str = ""):
    if not project or not file:
        raise HTTPException(status_code=400, detail="Select a project and file.")
    full_path = os.path.join(VIRALS_DIR, project, "subs", file)
    rows = editor.load_transcription_for_editor(full_path)
    return {"path": full_path, "rows": rows, "status": f"Loaded {len(rows)} segments."}


@router.post("/api/editor/save")
def editor_save(payload: EditorSavePayload):
    if not payload.path:
        raise HTTPException(status_code=400, detail="No file loaded.")
    return {"status": editor.save_editor_changes(payload.path, payload.rows)}


@router.post("/api/editor/render-one")
def editor_render_one(payload: EditorRenderPayload):
    if not payload.path:
        raise HTTPException(status_code=400, detail="No file loaded.")
    try:
        jobs.write_subtitle_config(payload.settings or {})
    except Exception:
        pass
    return {"status": editor.render_specific_video(payload.path)}


@router.post("/api/editor/render-all")
def editor_render_all(payload: EditorRenderPayload):
    if not payload.project:
        raise HTTPException(status_code=400, detail="No project selected.")
    settings = payload.settings or {}
    cmd = [sys.executable, MAIN_SCRIPT_PATH, "--project-path", os.path.join(VIRALS_DIR, payload.project), "--workflow", "3", "--skip-prompts"]
    try:
        config_path = jobs.write_subtitle_config(settings)
        if config_path and os.path.exists(config_path):
            cmd.extend(["--subtitle-config", config_path])
    except Exception:
        pass
    try:
        subprocess.Popen(cmd, cwd=WORKING_DIR)
        return {"status": "Render All started in background... Check terminal/logs."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
