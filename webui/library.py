import os
import json
import urllib.parse
import gradio as gr

# Setup Virals Dir relative to this file
# This file is in webui/library.py
# VIRALS dir is in ../VIRALS (root of project)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.append(BASE_DIR)
from i18n.i18n import I18nAuto
i18n = I18nAuto()

VIRALS_DIR = os.path.join(BASE_DIR, "VIRALS")


# URL Mode: "fastapi" (default) or "gradio"
URL_MODE = "fastapi"

def set_url_mode(mode):
    global URL_MODE
    URL_MODE = mode

def get_existing_projects():
    if not os.path.exists(VIRALS_DIR):
        return []
    try:
        projects = [d for d in os.listdir(VIRALS_DIR) if os.path.isdir(os.path.join(VIRALS_DIR, d))]
        projects.sort(key=lambda x: os.path.getctime(os.path.join(VIRALS_DIR, x)), reverse=True)
        return projects
    except:
        return []

def refresh_projects():
    projs = get_existing_projects()
    return gr.update(choices=projs, value=None)

def _safe_segment_base_name(index, segment):
    title = segment.get("title", f"Segment {index + 1}")
    safe_title = "".join(
        character for character in str(title) if character.isalnum() or character in " _-"
    ).strip()
    safe_title = safe_title.replace(" ", "_")[:60]
    return f"{index:03d}_{safe_title}" if safe_title else f"{index:03d}_Segment_{index + 1}"


def _find_segment_video(project_folder_path, index, segment):
    idx_str = f"{index:03d}"
    base_name = _safe_segment_base_name(index, segment)
    burned_sub_dir = os.path.join(project_folder_path, "burned_sub")
    final_dir = os.path.join(project_folder_path, "final")
    cuts_dir = os.path.join(project_folder_path, "cuts")
    candidates = []

    raw_path = segment.get("filepath")
    if isinstance(raw_path, str) and raw_path.strip():
        candidates.append(raw_path if os.path.isabs(raw_path) else os.path.join(project_folder_path, raw_path))

    filename = segment.get("filename")
    if isinstance(filename, str) and filename.strip():
        candidates.extend([
            os.path.join(burned_sub_dir, filename),
            os.path.join(final_dir, filename),
            os.path.join(cuts_dir, filename),
            os.path.join(project_folder_path, filename),
        ])

    candidates.extend([
        os.path.join(burned_sub_dir, f"{base_name}_processed_subtitled.mp4"),
        os.path.join(burned_sub_dir, f"{base_name}_subtitled.mp4"),
        os.path.join(final_dir, f"{base_name}.mp4"),
        os.path.join(cuts_dir, f"{base_name}_original_scale.mp4"),
        os.path.join(burned_sub_dir, f"final-output{idx_str}_processed_subtitled.mp4"),
        os.path.join(burned_sub_dir, f"output{idx_str}.mp4"),
        os.path.join(final_dir, f"final-output{idx_str}_processed.mp4"),
        os.path.join(project_folder_path, f"final-output{idx_str}_processed.mp4"),
        os.path.join(project_folder_path, f"output{idx_str}_original_scale.mp4"),
        os.path.join(project_folder_path, f"output{idx_str}.mp4"),
        os.path.join(cuts_dir, f"output{idx_str}_original_scale.mp4"),
        os.path.join(cuts_dir, f"segment_{idx_str}.mp4"),
        os.path.join(cuts_dir, f"{idx_str}.mp4"),
    ])

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    for directory in [burned_sub_dir, final_dir, cuts_dir, project_folder_path]:
        if not os.path.isdir(directory):
            continue
        for filename in sorted(os.listdir(directory)):
            filename_lower = filename.lower()
            if (
                filename_lower.endswith(".mp4")
                and "input" not in filename_lower
                and (filename.startswith(idx_str) or idx_str in filename)
            ):
                return os.path.join(directory, filename)

    return None

def generate_project_gallery(project_path_name, is_full_path=False):
    """
    Generates HTML gallery for a given project folder using FastAPI Static Files mounting.
    """
    if not project_path_name:
        return f'<div class="vc-gallery-empty">{i18n("No project selected.")}</div>'
    
    # Determine absolute path to project folder
    if is_full_path:
        project_folder_path = project_path_name
    else:
        project_folder_path = os.path.join(VIRALS_DIR, project_path_name)

    if not os.path.exists(project_folder_path):
        return f'<div class="vc-gallery-empty">{i18n("Project path not found: {}").format(project_folder_path)}</div>'

    try:
        # Load JSON
        json_path = os.path.join(project_folder_path, "viral_segments.txt")
        segments_data = {}
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                segments_data = json.load(f)
        
        segments_list = segments_data.get("segments", [])
        
        # Fallback if list is empty
        if not segments_list:
             found_files = []
             for subdir in ["burned_sub", "final", "cuts", "."]:
                 d = os.path.join(project_folder_path, subdir)
                 if os.path.exists(d):
                     for f in os.listdir(d):
                         if f.endswith(".mp4") and "input" not in f.lower():
                             found_files.append(os.path.join(d, f))
             found_files = sorted(list(set(found_files)))
             segments_list = [{"title": os.path.basename(f), "score": "N/A", "description": "No metadata found.", "filepath": f} for f in found_files]

        html_cards = ""
        
        for i, seg in enumerate(segments_list):
            download_link = ""
            export_link = ""
            title = seg.get("title", f"{i18n('Segment')} {i+1}")
            score = seg.get("score", "N/A")
            description = seg.get("description", i18n("No description available."))
            
            video_path = _find_segment_video(project_folder_path, i, seg)

            video_tag = ""
            if video_path:
                try:
                    abs_video = os.path.abspath(video_path)
                    
                    if URL_MODE == "gradio":
                         # Gradio Launch Mode
                         # Strategy: SMART PATH (Relative preferred, Absolute fallback)
                         
                         try:
                             cwd = os.getcwd()
                             abs_video_path = os.path.abspath(video_path)
                             
                             # Try relative path first
                             rel_path = os.path.relpath(abs_video_path, cwd)
                             
                             if not rel_path.startswith(".."):
                                 # Inside CWD, use relative
                                 final_path = rel_path.replace("\\", "/")
                                 # Debug
                                 print(f"DEBUG: URL Generation (Relative): {final_path}")
                             else:
                                 # Outside CWD, use absolute
                                 final_path = abs_video_path.replace("\\", "/")
                                 print(f"DEBUG: URL Generation (Absolute fallback): {final_path}")

                             # Encode
                             path_encoded = urllib.parse.quote(final_path, safe="/:")
                             video_src = f"/file/{path_encoded}"
                             
                         except Exception as e:
                             print(f"DEBUG: Error pathing: {e}")
                             video_src = ""
                         
                         if os.path.exists(abs_video):
                             print(f"DEBUG:   File Exists.")
                         else:
                             print(f"DEBUG:   File NOT FOUND.")
                             
                         video_tag = f"""
                        <video class="vc-gallery-video" controls preload="metadata" playsinline>
                            <source src="{video_src}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                        """
                         download_link = f'<a class="vc-gallery-action" href="{video_src}" target="_blank" download="{os.path.basename(video_path)}" title="Download"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg></a>'

                    else:
                        # Use Relative Path through /virals mount
                        # Calculate relative path from VIRALS_DIR
                        # video_path needs to be under VIRALS_DIR for this to work
                        abs_virals = os.path.abspath(VIRALS_DIR)
                        
                        if abs_video.startswith(abs_virals):
                            rel_path = os.path.relpath(abs_video, abs_virals)
                            # Replace backslashes for URL
                            url_path = rel_path.replace("\\", "/")
                            url_path = urllib.parse.quote(url_path)
                            
                            # Add timestamp to force cache refresh
                            import time
                            timestamp = int(time.time())
                            video_src = f"/virals/{url_path}?t={timestamp}"
                            
                            video_tag = f"""
                            <video class="vc-gallery-video" controls preload="metadata" playsinline>
                                <source src="{video_src}" type="video/mp4">
                                Your browser does not support the video tag.
                            </video>
                            """
                            download_link = f'<a class="vc-gallery-action" href="{video_src}" download="{os.path.basename(video_path)}" title="Download"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg></a>'
                            
                            # Export XML Link
                            # project_path_name might be full path or folder name
                            proj_name_api = os.path.basename(project_path_name)
                            
                            def make_export_btn(fmt, label, svg_path):
                                src = f"/export_xml_api?project={proj_name_api}&segment={i}&format={fmt}"
                                return f'<a class="vc-gallery-action" href="{src}" target="_blank" title="{label}"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{svg_path}</svg></a>'

                            # Premiere (Pr)
                            export_pr = make_export_btn("premiere", "Export Premiere XML (Split Screen – known bug)", '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M9 15h6"></path><path d="M12 12v6"></path>')
                            
                            # Resolve (Dv)
                            # export_dv = make_export_btn("resolve", "Export DaVinci Resolve XML", "#ff6464", '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><circle cx="12" cy="14" r="3"></circle>')
                            
                            # Final Cut (Fc)
                            # export_fc = make_export_btn("final-cut-pro", "Export FCP XML", "#64d0ff", '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M10 12l4 2l-4 2z"></path>')

                            export_link = f"{export_pr}" #{export_dv}{export_fc}"

                        else:
                            video_tag = f'<div class="vc-gallery-missing">{i18n("External Video")}</div>'
                except Exception as e:
                    video_tag = f'<div class="vc-gallery-missing">{i18n("Error: {}").format(str(e))}</div>'

            else:
                video_tag = f'<div class="vc-gallery-missing">{i18n("Not Found")}</div>'

            score_mod = "vc-score-na"
            try:
                val = int(score)
                if val < 70:
                    score_mod = "vc-score-low"
                elif val < 85:
                    score_mod = "vc-score-mid"
                else:
                    score_mod = "vc-score-ok"
            except Exception:
                pass
            safe_title = str(title).replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")

            html_cards += f"""
            <article class="vc-gallery-card">
                <div class="vc-gallery-player">{video_tag}</div>
                <div class="vc-gallery-meta">
                    <div class="vc-gallery-meta-row">
                        <span class="vc-gallery-score {score_mod}">{score}</span>
                        <div class="vc-gallery-actions">{export_link}{download_link}</div>
                    </div>
                    <h4 class="vc-gallery-title" title="{safe_title}">{safe_title}</h4>
                </div>
            </article>
            """
        
        if not html_cards:
             return f'<div class="vc-gallery-empty">{i18n("No viral segments found.")}</div>'

        return f'<div class="vc-gallery">{html_cards}</div>'

    except Exception as e:
        return i18n("Error loading gallery: {}").format(e)
