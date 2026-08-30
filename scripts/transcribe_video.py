import os
import sys
import json
import time
import re
import uuid
import base64
import subprocess
import urllib.request
import urllib.error
from io import BytesIO
from i18n.i18n import I18nAuto

i18n = I18nAuto()

CHUNK_SECONDS = 45
WHISPER_BACKENDS = ("cloudflare", "groq")


def _load_api_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api_config.json")
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao ler api_config.json: {e}")
        return {}


def _resolve_backend(model_name, config):
    name = (model_name or "").strip().lower()
    if name in WHISPER_BACKENDS:
        return name
    if "groq" in name:
        return "groq"
    if "cloudflare" in name or name.startswith("@cf/"):
        return "cloudflare"
    configured = (config.get("whisper_backend") or "cloudflare").strip().lower()
    if configured in WHISPER_BACKENDS:
        return configured
    return "cloudflare"


def parse_srt(srt_path):
    print(f"Parsing SRT: {srt_path}")
    segments = []
    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = content.replace("\r\n", "\n")
        blocks = content.strip().split("\n\n")

        def time_to_seconds(t_str):
            t_str = t_str.replace(",", ".")
            parts = t_str.split(":")
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            if len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s)
            return 0.0

        for block in blocks:
            lines = block.split("\n")
            for i, line in enumerate(lines):
                if "-->" in line:
                    start_str, end_str = line.split(" --> ")
                    text_lines = lines[i + 1:]
                    text = " ".join(text_lines).strip()
                    text = re.sub(r"<[^>]+>", "", text)
                    if text:
                        segments.append({
                            "start": time_to_seconds(start_str.strip()),
                            "end": time_to_seconds(end_str.strip().split(" ")[0]),
                            "text": text,
                        })
                    break
    except Exception as e:
        print(f"Error parsing SRT {srt_path}: {e}")
        return None
    return segments


def parse_vtt(vtt_path):
    print(f"Parsing VTT: {vtt_path}")
    segments = []
    try:
        with open(vtt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        def vtt_time_to_seconds(t_str):
            t_str = t_str.strip()
            parts = t_str.split(":")
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            if len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s)
            return 0.0

        current_entry = {"text": []}
        for line in lines:
            line = line.strip()
            if not line:
                if "start" in current_entry and current_entry["text"]:
                    full_text = " ".join(current_entry["text"]).strip()
                    full_text = re.sub(r"<[^>]+>", "", full_text)
                    full_text = re.sub(r"&[^;]+;", "", full_text)
                    if full_text:
                        segments.append({
                            "start": current_entry["start"],
                            "end": current_entry["end"],
                            "text": full_text,
                        })
                current_entry = {"text": []}
                continue
            if line.startswith("WEBVTT") or line.startswith("X-TIMESTAMP-MAP") or line.startswith("NOTE"):
                continue
            if "-->" in line:
                times = line.split("-->")
                current_entry["start"] = vtt_time_to_seconds(times[0])
                current_entry["end"] = vtt_time_to_seconds(times[1].strip().split(" ")[0])
            elif "start" in current_entry:
                current_entry["text"].append(line)

        if "start" in current_entry and current_entry["text"]:
            full_text = " ".join(current_entry["text"]).strip()
            full_text = re.sub(r"<[^>]+>", "", full_text)
            if full_text:
                segments.append({
                    "start": current_entry["start"],
                    "end": current_entry["end"],
                    "text": full_text,
                })
    except Exception as e:
        print(f"Error parsing VTT {vtt_path}: {e}")
        return None
    return segments


def _seconds_to_srt(t):
    if t < 0:
        t = 0
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def _words_from_text(text, start, end):
    tokens = [w for w in re.findall(r"\S+", text or "") if w]
    if not tokens:
        return []
    dur = max(0.01, float(end) - float(start))
    step = dur / len(tokens)
    words = []
    for i, token in enumerate(tokens):
        words.append({
            "word": token,
            "start": start + i * step,
            "end": start + (i + 1) * step,
        })
    return words


def _normalize_word(item, offset=0.0):
    if not isinstance(item, dict):
        return None
    token = item.get("word") or item.get("text") or ""
    token = str(token).strip()
    if not token:
        return None
    try:
        w_start = float(item.get("start", 0)) + offset
        w_end = float(item.get("end", w_start)) + offset
    except (TypeError, ValueError):
        return None
    return {"word": token, "start": w_start, "end": w_end}


def _normalize_segments(raw_segments, offset=0.0):
    normalized = []
    if not raw_segments:
        return normalized
    for seg in raw_segments:
        if not isinstance(seg, dict):
            continue
        text = (seg.get("text") or "").strip()
        try:
            start = float(seg.get("start", 0)) + offset
            end = float(seg.get("end", start)) + offset
        except (TypeError, ValueError):
            continue
        if end <= start:
            end = start + 0.01
        words = []
        for item in seg.get("words") or []:
            word = _normalize_word(item, offset)
            if word:
                words.append(word)
        if not words and text:
            words = _words_from_text(text, start, end)
        if not text and words:
            text = " ".join(w["word"] for w in words)
        if not text:
            continue
        normalized.append({"start": start, "end": end, "text": text, "words": words})
    return normalized


def _write_outputs(result, output_folder, base_name):
    srt_file = os.path.join(output_folder, f"{base_name}.srt")
    tsv_file = os.path.join(output_folder, f"{base_name}.tsv")
    json_file = os.path.join(output_folder, f"{base_name}.json")
    segments = result.get("segments") or []

    with open(srt_file, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{_seconds_to_srt(seg['start'])} --> {_seconds_to_srt(seg['end'])}\n")
            f.write(f"{seg.get('text', '').strip()}\n\n")

    with open(tsv_file, "w", encoding="utf-8") as f:
        f.write("start\tend\ttext\n")
        for seg in segments:
            start_ms = int(round(float(seg["start"]) * 1000))
            end_ms = int(round(float(seg["end"]) * 1000))
            text = (seg.get("text") or "").replace("\t", " ").replace("\n", " ")
            f.write(f"{start_ms}\t{end_ms}\t{text}\n")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return srt_file, tsv_file


def _run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def _extract_audio(input_file, audio_path):
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", input_file, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", audio_path,
    ]
    result = _run_cmd(cmd)
    if result.returncode != 0 or not os.path.exists(audio_path):
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"ffmpeg audio extract failed: {err}")


def _audio_duration(audio_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path,
    ]
    result = _run_cmd(cmd)
    try:
        return float((result.stdout or "").strip())
    except ValueError:
        raise RuntimeError("ffprobe could not read audio duration")


def _cut_audio_chunk(audio_path, chunk_path, start, duration):
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(start), "-t", str(duration), "-i", audio_path, "-c", "copy", chunk_path,
    ]
    result = _run_cmd(cmd)
    if result.returncode != 0 or not os.path.exists(chunk_path):
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"ffmpeg chunk failed: {err}")


def _http_json(url, headers, payload, timeout=180):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} {url}: {body}") from e


def _http_multipart(url, headers, fields, files, timeout=180):
    boundary = "----ViralCutter" + uuid.uuid4().hex
    body = BytesIO()
    for key, value in fields:
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body.write(str(value).encode("utf-8") + b"\r\n")
    for name, filename, content, ctype in files:
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
        body.write(f"Content-Type: {ctype}\r\n\r\n".encode())
        body.write(content)
        body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode())
    data = body.getvalue()
    req = urllib.request.Request(url, data=data, method="POST")
    for key, value in headers.items():
        req.add_header(key, value)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} {url}: {body_err}") from e


def _transcribe_cloudflare_chunk(chunk_path, account_id, api_token, model_name):
    with open(chunk_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("ascii")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_name}"
    payload = {
        "audio": audio_b64,
        "task": "transcribe",
        "vad_filter": True,
    }
    data = _http_json(
        url,
        {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
        payload,
    )
    if data.get("success") is False:
        raise RuntimeError(f"Cloudflare whisper error: {data.get('errors')}")
    result = data.get("result") or data
    segments = result.get("segments") or []
    if not segments and result.get("vtt"):
        vtt_path = chunk_path + ".vtt"
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(result["vtt"])
        segments = parse_vtt(vtt_path) or []
        try:
            os.remove(vtt_path)
        except OSError:
            pass
    language = result.get("language") or result.get("transcription_info", {}).get("language") or "en"
    return segments, language


def _transcribe_groq_chunk(chunk_path, api_key, model_name):
    with open(chunk_path, "rb") as f:
        audio_bytes = f.read()
    data = _http_multipart(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        {"Authorization": f"Bearer {api_key}"},
        [
            ("model", model_name),
            ("response_format", "verbose_json"),
            ("timestamp_granularities[]", "word"),
            ("timestamp_granularities[]", "segment"),
        ],
        [("file", os.path.basename(chunk_path), audio_bytes, "audio/mpeg")],
    )
    return data.get("segments") or [], data.get("language") or "en"


def _transcribe_audio(audio_path, backend, config):
    duration = _audio_duration(audio_path)
    print(f"Audio duration: {duration:.1f}s | backend: {backend}")
    all_segments = []
    language = "en"
    tmp_dir = os.path.dirname(audio_path)
    start = 0.0
    chunk_idx = 0

    while start < duration:
        remain = duration - start
        if remain < 0.4:
            break
        chunk_len = min(CHUNK_SECONDS, remain)
        chunk_path = os.path.join(tmp_dir, f"whisper_chunk_{chunk_idx}.mp3")
        _cut_audio_chunk(audio_path, chunk_path, start, chunk_len)
        print(f"Transcribing chunk {chunk_idx + 1} ({start:.1f}s -> {start + chunk_len:.1f}s) via {backend}...")

        last_error = None
        for attempt in range(3):
            try:
                if backend == "groq":
                    groq_cfg = config.get("groq") or {}
                    api_key = groq_cfg.get("api_key") or ""
                    if not api_key:
                        raise RuntimeError("Groq API key missing in api_config.json -> groq.api_key")
                    model_name = groq_cfg.get("whisper_model") or "whisper-large-v3-turbo"
                    raw_segments, language = _transcribe_groq_chunk(chunk_path, api_key, model_name)
                else:
                    cf_cfg = config.get("cloudflare") or {}
                    account_id = cf_cfg.get("account_id") or ""
                    api_token = cf_cfg.get("api_token") or ""
                    if not account_id or not api_token:
                        raise RuntimeError("Cloudflare account_id/api_token missing in api_config.json")
                    model_name = cf_cfg.get("whisper_model") or "@cf/openai/whisper-large-v3-turbo"
                    raw_segments, language = _transcribe_cloudflare_chunk(chunk_path, account_id, api_token, model_name)
                all_segments.extend(_normalize_segments(raw_segments, offset=start))
                last_error = None
                break
            except Exception as e:
                last_error = e
                print(f"[WARN] Whisper chunk failed (attempt {attempt + 1}/3): {e}")
                time.sleep(2 * (attempt + 1))
        try:
            os.remove(chunk_path)
        except OSError:
            pass
        if last_error:
            raise last_error
        start += chunk_len
        chunk_idx += 1

    return {"segments": all_segments, "language": language}


def transcribe(input_file, model_name="cloudflare", project_folder="tmp"):
    print(i18n(f"Iniciando transcrição de {input_file}..."))
    print(f"DEBUG: Python: {sys.executable}")
    start_time = time.time()

    if project_folder is None:
        project_folder = os.path.dirname(input_file) or "tmp"

    output_folder = project_folder
    os.makedirs(output_folder, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    srt_file = os.path.join(output_folder, f"{base_name}.srt")
    tsv_file = os.path.join(output_folder, f"{base_name}.tsv")
    json_file = os.path.join(output_folder, f"{base_name}.json")

    if os.path.exists(srt_file) and os.path.exists(tsv_file) and os.path.exists(json_file):
        print("Os arquivos SRT, TSV e JSON já existem. Pulando a transcrição.")
        return srt_file, tsv_file

    config = _load_api_config()
    backend = _resolve_backend(model_name, config)
    print(f"Whisper backend: {backend} (whisper-large-v3-turbo)")

    start_segments = None
    if os.path.exists(os.path.join(output_folder, "input.srt")):
        start_segments = parse_srt(os.path.join(output_folder, "input.srt"))
    elif os.path.exists(os.path.join(output_folder, "input.vtt")):
        start_segments = parse_vtt(os.path.join(output_folder, "input.vtt"))

    try:
        if start_segments:
            print("--- MODO LEGENDAS YOUTUBE (sem ASR) ---")
            result = {
                "segments": _normalize_segments(start_segments),
                "language": "en",
            }
        else:
            audio_path = os.path.join(output_folder, f"{base_name}_whisper.mp3")
            print(f"Extracting audio: {input_file}")
            _extract_audio(input_file, audio_path)
            result = _transcribe_audio(audio_path, backend, config)
            try:
                os.remove(audio_path)
            except OSError:
                pass

        print("Salvando resultados...")
        srt_file, tsv_file = _write_outputs(result, output_folder, base_name)
        elapsed = time.time() - start_time
        print(f"Processamento concluído em {int(elapsed // 60)}m {int(elapsed % 60)}s.")
    except Exception as e:
        print(f"ERRO CRÍTICO na transcrição: {e}")
        import traceback
        traceback.print_exc()
        raise

    if not os.path.exists(srt_file):
        print(f"AVISO: Arquivo SRT {srt_file} não encontrado após execução.")
    return srt_file, tsv_file
