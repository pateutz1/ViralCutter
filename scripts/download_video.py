import os
import re
import shutil
import yt_dlp
import sys
from i18n.i18n import I18nAuto
i18n = I18nAuto()

def sanitize_filename(name):
    """Remove invalid characters and emojis to avoid encoding errors on Windows."""
    # Remove filesystem reserved characters
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    
    # Remove emojis and characters unsupported by the Windows console (CP1252)
    # This keeps accents (á, ç, é) but removes 😱, etc.
    try:
        cleaned = cleaned.encode('cp1252', 'ignore').decode('cp1252')
    except:
        # Fallback if CP1252 is unavailable: strip all non-ascii (removes accents)
        cleaned = cleaned.encode('ascii', 'ignore').decode('ascii')
        
    cleaned = cleaned.strip()
    return cleaned

def progress_hook(d):
    if d['status'] == 'downloading':
        try:
            p = d.get('_percent_str', '').replace('%','')
            print(f"[download] {p}% - {d.get('_eta_str', 'N/A')} remaining", flush=True)
        except:
            pass
    elif d['status'] == 'finished':
        print(f"[download] Download completed: {d['filename']}", flush=True)


def _detect_js_runtimes():
    """Prefer Node (installed on most Windows setups); fall back to Deno if present."""
    runtimes = {}
    node = shutil.which("node")
    if node:
        runtimes["node"] = {"path": node}
    deno = shutil.which("deno")
    if deno:
        runtimes["deno"] = {"path": deno}
    return runtimes


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_cookie_opts():
    """Cookies file (preferred) or browser export via YTDLP_COOKIES_FROM_BROWSER."""
    cookie_file = (os.environ.get("YTDLP_COOKIES_FILE") or "").strip()
    if not cookie_file:
        default = os.path.join(_project_root(), "cookies.txt")
        if os.path.isfile(default):
            cookie_file = default
    if cookie_file and os.path.isfile(cookie_file):
        print(f"[yt-dlp] Using cookies file: {cookie_file}")
        return {"cookiefile": cookie_file}

    browser = (os.environ.get("YTDLP_COOKIES_FROM_BROWSER") or "").strip().lower()
    if browser in ("chrome", "edge", "firefox", "brave", "opera", "chromium"):
        print(f"[yt-dlp] Using cookies from browser: {browser}")
        return {"cookiesfrombrowser": (browser,)}
    return {}


def _base_ydl_opts(**extra):
    """Shared yt-dlp options: JS runtime + EJS remote components, no Chrome cookie lock."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "remote_components": ["ejs:github"],
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        "force_ipv4": True,
    }
    js_runtimes = _detect_js_runtimes()
    if js_runtimes:
        opts["js_runtimes"] = js_runtimes
    opts.update(extra)
    return opts


SUBTITLE_LANGS = ["pt.*", "en.*", "es.*"]


def _format_vtt_lines(lines):
    """Convert YouTube VTT lines to SRT blocks, ignoring text outside timed cues."""
    srt_content = []
    counter = 1
    last_text = ""
    current_start = None
    current_end = None

    def fix_time(value):
        value = value.replace(".", ",")
        return "00:" + value if value.count(":") == 1 else value

    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            current_start = None
            current_end = None
            continue
        if clean_line.startswith(("WEBVTT", "X-TIMESTAMP", "NOTE", "Kind:", "Language:")):
            current_start = None
            current_end = None
            continue
        if "-->" in clean_line:
            parts = clean_line.split("-->", 1)
            start = parts[0].strip()
            end = parts[1].strip().split(" ")[0]
            current_start = fix_time(start)
            current_end = fix_time(end)
            continue
        if current_start is None or current_end is None:
            continue

        text = re.sub(r"<[^>]+>", "", clean_line).strip()
        final_line = text.split("\n")[-1].strip()
        if not final_line or final_line == last_text:
            continue
        srt_content.extend([
            f"{counter}\n",
            f"{current_start} --> {current_end}\n",
            f"{final_line}\n\n",
        ])
        last_text = final_line
        counter += 1

    return srt_content

def download(url, base_root="VIRALS", download_subs=True, quality="best"):
    # 1. Extract video info to get the title
    print(i18n("Extracting video information..."))
    title = None
    js_runtimes = _detect_js_runtimes()
    if js_runtimes:
        print(f"[yt-dlp] JS runtime: {', '.join(js_runtimes.keys())}")
    else:
        print("[yt-dlp] WARNING: No Node/Deno found. Install Node.js 20+ for full YouTube format support.")

    cookie_opts = _resolve_cookie_opts()
    try:
        with yt_dlp.YoutubeDL(_base_ydl_opts(**cookie_opts)) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title")
    except Exception as e:
        if cookie_opts:
            try:
                print(i18n("Warning: Failed to extract info with cookies: {}").format(e))
            except UnicodeEncodeError:
                print(i18n("Warning: Failed to extract info with cookies: [Encoding Error in Message]"))
            try:
                with yt_dlp.YoutubeDL(_base_ydl_opts()) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get("title")
            except Exception as e2:
                try:
                    print(i18n("Error getting video info (without cookies): {}").format(e2))
                except UnicodeEncodeError:
                    print(i18n("Error getting video info (without cookies): [Encoding Error in Message]"))
        else:
            try:
                print(i18n("Error getting video info (without cookies): {}").format(e))
            except UnicodeEncodeError:
                print(i18n("Error getting video info (without cookies): [Encoding Error in Message]"))

    # Final fallback
    if title:
        safe_title = sanitize_filename(title)
        try:
            print(i18n("Detected title: {}").format(title))
        except UnicodeEncodeError:
            # Fallback for Windows consoles that choke on Emojis
            clean_title = title.encode('ascii', 'replace').decode('ascii')
            print(i18n("Detected title: {}").format(clean_title))
    else:
        print(i18n("WARNING: Title could not be obtained. Using 'Unknown_Video'."))
        safe_title = i18n("Unknown_Video")

    # 2. Create folder structure
    project_folder = os.path.join(base_root, safe_title)
    os.makedirs(project_folder, exist_ok=True)
    
    # Final video path
    output_filename = 'input' 
    output_path_base = os.path.join(project_folder, output_filename)
    final_video_path = f"{output_path_base}.mp4"

    # Smart check
    if os.path.exists(final_video_path):
        if os.path.getsize(final_video_path) > 1024: 
            try:
                print(i18n("Video already exists at: {}").format(final_video_path))
            except UnicodeEncodeError:
                print(i18n("Video already exists at: {}").format(final_video_path.encode('ascii', 'replace').decode('ascii')))
            print(i18n("Skipping download and reusing local file."))
            return final_video_path, project_folder
        else:
            print(i18n("Existing file found but seems corrupted/empty. Downloading again..."))
            try:
                os.remove(final_video_path)
            except:
                pass

    # Temp cleanup
    temp_path = f"{output_path_base}.temp.mp4"
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except:
            pass

    # Quality mapping
    quality_map = {
        "best": 'bestvideo+bestaudio/best',
        "1080p": 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        "720p": 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        "480p": 'bestvideo[height<=480]+bestaudio/best[height<=480]'
    }
    selected_format = quality_map.get(quality, 'bestvideo+bestaudio/best')
    print(i18n("Configuring download quality: {} -> {}").format(quality, selected_format))

    ydl_opts = _base_ydl_opts(
        format=selected_format,
        overwrites=True,
        outtmpl=output_path_base,
        postprocessor_args=["-movflags", "faststart"],
        merge_output_format="mp4",
        progress_hooks=[progress_hook],
        writesubtitles=download_subs,
        writeautomaticsub=download_subs,
        subtitleslangs=SUBTITLE_LANGS,
        skip_download=False,
        quiet=False,
        no_warnings=True,
    )
    ydl_opts.update(cookie_opts)

    
    if download_subs:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegSubtitlesConvertor',
            'format': 'srt',
        }]

    try:
        print(i18n("Downloading video to: {}...").format(project_folder))
    except UnicodeEncodeError:
        print(i18n("Downloading video to: {}...").format(project_folder.encode('ascii', 'replace').decode('ascii')))
    
    # Attempt 1: With original configuration
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        error_str = str(e)
        if "No address associated with hostname" in error_str or "Failed to resolve" in error_str:
            print(i18n("\n[CRITICAL ERROR] Connection Failure: Could not access YouTube."))
            print(i18n("Check your internet connection or if there is any DNS block."))
            print(i18n("Details: {}").format(e))
            sys.exit(1)
        
        elif download_subs and ("Unable to download video subtitles" in error_str or "429" in error_str):
            print(i18n("\nWarning: Error downloading subtitles ({}).").format(e))
            print(i18n("Retrying ONLY the video (without subtitles)..."))
            
            ydl_opts['writesubtitles'] = False
            ydl_opts['writeautomaticsub'] = False
            ydl_opts['postprocessors'] = [p for p in ydl_opts.get('postprocessors', []) if 'Subtitle' not in p.get('key', '')]
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e2:
                print(i18n("Fatal error on second attempt: {}").format(e2))
                raise
        elif "is not a valid URL" in error_str:
             print(i18n("Error: the entered link is not valid."))
             raise 
        else:
            print(i18n("Download error: {}").format(e))
            raise
    except Exception as e:
        print(i18n("Unexpected error: {}").format(e))
        raise

    # RENAME SUBTITLE TO STANDARD (input.vtt or input.srt)
    # If VTT, convert to SRT to ensure compatibility.
    try:
        import glob
        # Take the first one found
        potential_subs = glob.glob(os.path.join(project_folder, "input.*.vtt")) + glob.glob(os.path.join(project_folder, "input.*.srt"))
        
        if potential_subs:
            best_sub = potential_subs[0]
            ext = os.path.splitext(best_sub)[1]
            new_name = os.path.join(project_folder, "input.srt") # Standardize everything to .srt
            
            if ext.lower() == '.vtt':
                try:
                    print(i18n("Formatting complex VTT subtitle ({}) to clean SRT...").format(os.path.basename(best_sub)))
                except UnicodeEncodeError:
                    print(i18n("Formatting complex VTT subtitle ({}) to clean SRT...").format(os.path.basename(best_sub).encode('ascii', 'replace').decode('ascii')))
                try:
                    with open(best_sub, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    srt_content = _format_vtt_lines(lines)
                    
                    with open(new_name, 'w', encoding='utf-8') as f_out:
                        f_out.writelines(srt_content)
                    
                    try:
                        print(i18n("Subtitle converted and cleaned: {}").format(new_name))
                    except UnicodeEncodeError:
                        print(i18n("Subtitle converted and cleaned: {}").format(new_name.encode('ascii', 'replace').decode('ascii')))
                    try: os.remove(best_sub) 
                    except: pass
                    
                except Exception as e_conv:
                    print(i18n("Failed to convert VTT: {}. Keeping original.").format(e_conv))
                    # Fallback: rename only
                    new_name_fallback = os.path.join(project_folder, "input.vtt")
                    if os.path.exists(new_name_fallback) and new_name_fallback != best_sub:
                        try: os.remove(new_name_fallback)
                        except: pass
                    os.rename(best_sub, new_name_fallback)

            else:
                # Already SRT, just rename
                if os.path.exists(new_name) and new_name != best_sub:
                    try: os.remove(new_name)
                    except: pass
                os.rename(best_sub, new_name)
                try:
                    print(i18n("SRT subtitle renamed to: {}").format(new_name))
                except UnicodeEncodeError:
                    print(i18n("SRT subtitle renamed to: {}").format(new_name.encode('ascii', 'replace').decode('ascii')))
            
            # Clean leftovers
            for extra in potential_subs[1:]:
                try: os.remove(extra)
                except: pass

    except Exception as e_ren:
        print(i18n("Error processing subtitles: {}").format(e_ren))

    return final_video_path, project_folder