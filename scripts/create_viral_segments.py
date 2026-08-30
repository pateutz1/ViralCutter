import json
import os
import re
import sys
import time
import ast
import io
import subprocess
import urllib.request
import urllib.error

# Configure stdout to avoid encoding errors on Windows (replace invalid characters with ?)
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    try:
        # Keep original encoding but ignore errors (replace with ?)
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=sys.stdout.encoding or 'utf-8', errors='replace', line_buffering=True)
    except:
        pass

# Try importing optional AI libraries
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    import g4f
    HAS_G4F = True
except ImportError:
    HAS_G4F = False

def clean_json_response(response_text):
    """
    Clean the response focusing on finding the JSON object that contains the "segments" key.
    Strategy:
    1. Search for the word "segments", find the preceding '{', and use raw_decode.
    2. Fallback: Parse the segment list item by item (recovery of truncated JSON).
    """
    if not isinstance(response_text, str):
        response_text = str(response_text)
    
    if not response_text:
        return {"segments": []}

    # 1. Preliminary cleanup
    # Remove thinking tags (DeepSeek R1)
    response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
    
    # Normalize excessive escapes (\n becoming \\n) and quotes if needed
    try:
        if "\\n" in response_text or "\\\"" in response_text:
             # Try a basic escape decode
             response_text = response_text.replace("\\n", "\n").replace("\\\"", "\"").replace("\\'", "'")
    except:
        pass

    # 2. Search for the "segments" keyword
    # Find indices of all occurrences of 'segments'
    matches = [m.start() for m in re.finditer(r'segments', response_text)]
    
    if not matches:
        # If segments not found, return empty
        return {"segments": []}

    # Try extracting valid JSON from each occurrence
    for match_idx in matches:
        # Find the nearest '{' BEFORE "segments"
        # Limit search to 5000 chars backward for performance
        start_search = max(0, match_idx - 5000)
        snippet_before = response_text[start_search:match_idx]
        
        # Find the LAST '{' in the snippet
        last_open_rel = snippet_before.rfind('{')
        
        if last_open_rel != -1:
            real_start = start_search + last_open_rel
            candidate_text = response_text[real_start:]
            
            # Attempt A: json.raw_decode
            try:
                decoder = json.JSONDecoder()
                obj, _ = decoder.raw_decode(candidate_text)
                if 'segments' in obj and isinstance(obj['segments'], list):
                    return obj
            except:
                pass
            
            # Attempt B: ast.literal_eval
            try:
                balance = 0
                in_string = False
                escape = False
                found_end = -1
                
                for i, char in enumerate(candidate_text):
                    if escape:
                        escape = False
                        continue
                    if char == '\\':
                        escape = True
                        continue
                    if char == "'" or char == '"':
                        in_string = not in_string
                        continue
                        
                    if not in_string:
                        if char == '{':
                            balance += 1
                        elif char == '}':
                            balance -= 1
                            if balance == 0:
                                found_end = i
                                break
                
                if found_end != -1:
                    clean_cand = candidate_text[:found_end+1]
                    obj = ast.literal_eval(clean_cand)
                    if 'segments' in obj and isinstance(obj['segments'], list):
                        return obj
            except:
                pass

    # 3. Fallback: Raw markdown extraction
    try:
        match = re.search(r"```json(.*?)```", response_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except:
        pass
        
    # 4. LAST RESORT: Fragment Parser (for truncated/incomplete JSON)
    # Look for "segments": [ and try parsing item by item
    try:
        match_list = re.search(r'"segments"\s*:\s*\[', response_text)
        if match_list:
            start_pos = match_list.end()
            current_pos = start_pos
            found_segments = []
            decoder = json.JSONDecoder()
            
            while True:
                while current_pos < len(response_text) and response_text[current_pos] in ' \t\n\r,':
                    current_pos += 1
                
                if current_pos >= len(response_text):
                    break
                    
                if response_text[current_pos] == ']':
                    break
                
                try:
                    obj, end_pos = decoder.raw_decode(response_text[current_pos:])
                    if isinstance(obj, dict):
                        found_segments.append(obj)
                    current_pos += end_pos
                except json.JSONDecodeError:
                    break
                    
            if found_segments:
                print(f"[INFO] Recovered {len(found_segments)} segments from truncated JSON.")
                return {"segments": found_segments}
    except:
        pass

    return {"segments": []}


def preprocess_transcript_for_ai(segments):
    """
    Concatenates transcript segments into a single string with embedded time tags.
    """
    if not segments:
        return ""

    full_text = ""
    last_tag_time = -100  # Force first tag
    
    # Try to start with (0s) based on first segment
    first_start = segments[0].get('start', 0)
    full_text += f"({int(first_start)}s) "
    last_tag_time = first_start

    for seg in segments:
        text = seg.get('text', '').strip()
        end_time = seg.get('end', 0)
        
        full_text += text + " "
        
        if end_time - last_tag_time >= 4:
            full_text += f"({int(end_time)}s) "
            last_tag_time = end_time

    return full_text.strip()

def call_gemini(prompt, api_key, model_name='gemini-2.5-flash-lite-preview-09-2025'):
    if not HAS_GEMINI:
        raise ImportError("The 'google-generativeai' library is not installed. Install with: pip install google-generativeai")
    
    genai.configure(api_key=api_key)
    # Using model defined in config or the default
    model = genai.GenerativeModel(model_name) 
    
    max_retries = 5
    base_wait = 30

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Quota exceeded" in error_str:
                wait_time = base_wait * (attempt + 1)
                
                match = re.search(r"retry in (\d+(\.\d+)?)s", error_str)
                if match:
                    wait_time = float(match.group(1)) + 5.0
                
                print(f"[429] Quota Exceeded. Waiting {wait_time:.2f}s before retry {attempt+1}/{max_retries}...", flush=True)
                time.sleep(wait_time)
                continue
            else:
                print(f"Error in Gemini API: {e}")
                return "{}"
    
    print("Failed after max retries on Gemini.")
    return "{}"

def call_g4f(prompt, model_name="gpt-4o-mini"):
    if not HAS_G4F:
        raise ImportError("The 'g4f' library is not installed. Install with: pip install g4f")
    
    max_retries = 3
    base_wait = 5
    
    for attempt in range(max_retries):
        try:
            response = g4f.ChatCompletion.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            
            if isinstance(response, dict):
                if 'error' in response:
                    raise Exception(f"API Error: {response['error']}")
                if 'choices' in response and isinstance(response['choices'], list):
                    if len(response['choices']) > 0:
                         content = response['choices'][0].get('message', {}).get('content', '')
                         if content:
                             return content
                if not response:
                     raise ValueError("Empty Dict response")

                return json.dumps(response)

            if not response:
                print(f"[WARN] G4F returned empty response. Attempt {attempt+1}/{max_retries}")
                time.sleep(base_wait)
                continue
            
            if isinstance(response, str):
                return response

            try:
                return json.dumps(response, ensure_ascii=False)
            except:
                return str(response)
            
        except Exception as e:
            print(f"[WARN] Error in G4F API (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = base_wait * (2 ** attempt)
                time.sleep(wait_time)
            
    print(f"Critical failure after {max_retries} attempts on G4F.")
    return "{}"

def _http_json(url, headers, payload, timeout=180):
    merged = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ViralCutter/1.0",
        "Accept": "application/json",
    }
    merged.update(headers)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=merged, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e

def _collect_text_parts(value):
    if isinstance(value, str) and value.strip():
        return [value]
    if isinstance(value, list):
        parts = []
        for part in value:
            if isinstance(part, str) and part.strip():
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text") or part.get("content")
                parts.extend(_collect_text_parts(text))
        return parts
    return []

def _extract_chat_text(data):
    if isinstance(data, str):
        return data
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") or {}
        for key in ("content", "reasoning", "text"):
            parts = _collect_text_parts(msg.get(key))
            if parts:
                return "\n".join(parts)
        if choices[0].get("text"):
            return choices[0]["text"]
    result = data.get("result", data)
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("response", "content", "text", "reasoning"):
            if result.get(key):
                parts = _collect_text_parts(result.get(key))
                if parts:
                    return "\n".join(parts)
        output = result.get("output")
        if isinstance(output, list):
            texts = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "reasoning":
                    continue
                texts.extend(_collect_text_parts(item.get("content") or item.get("text")))
            if texts:
                return "\n".join(texts)
    return ""

def call_groq(prompt, api_key, model_name="openai/gpt-oss-120b"):
    if not api_key:
        raise ValueError("Groq API key is required")
    messages = [
        {"role": "system", "content": "You are a helpful assistant that outputs only JSON."},
        {"role": "user", "content": prompt},
    ]
    payloads = [
        {"model": model_name, "messages": messages, "temperature": 0.4, "max_completion_tokens": 4096, "reasoning_effort": "low"},
        {"model": model_name, "messages": messages, "temperature": 0.4, "max_tokens": 4096},
    ]
    last_error = None
    for payload in payloads:
        try:
            data = _http_json(
                "https://api.groq.com/openai/v1/chat/completions",
                {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                payload,
            )
            text = _extract_chat_text(data)
            if text.strip():
                return text
            raise ValueError("Empty Groq response")
        except Exception as e:
            last_error = e
            print(f"[WARN] Groq error: {e}")
    print(f"Failed after max retries on Groq: {last_error}")
    return "{}"

def call_cloudflare(prompt, account_id, api_token, model_name="@cf/openai/gpt-oss-120b"):
    if not account_id or not api_token:
        raise ValueError("Cloudflare account_id and api_token are required")
    messages = [
        {"role": "system", "content": "You are a helpful assistant that outputs only JSON."},
        {"role": "user", "content": prompt},
    ]
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    attempts = [
        (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions",
            {"model": model_name, "messages": messages, "temperature": 0.4, "max_tokens": 4096, "reasoning_effort": "low"},
        ),
        (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_name}",
            {"messages": messages, "max_tokens": 4096, "temperature": 0.4, "reasoning": {"effort": "low"}},
        ),
    ]
    last_error = None
    for url, payload in attempts:
        try:
            data = _http_json(url, headers, payload)
            if data.get("success") is False:
                raise RuntimeError(f"Cloudflare error: {data.get('errors')}")
            text = _extract_chat_text(data)
            if text.strip():
                return text
            keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
            result_keys = list((data.get("result") or {}).keys()) if isinstance(data, dict) else []
            raise ValueError(f"Empty Cloudflare response keys={keys} result_keys={result_keys}")
        except Exception as e:
            last_error = e
            print(f"[WARN] Cloudflare LLM error: {e}")
    print(f"Failed after max retries on Cloudflare: {last_error}")
    return "{}"

def load_transcript(project_folder):
    """Parses input.tsv or input.srt from the project folder."""
    input_tsv = os.path.join(project_folder, 'input.tsv')
    input_srt = os.path.join(project_folder, 'input.srt')

    transcript_segments = []
    
    # Try to load TSV first (more reliable time)
    if os.path.exists(input_tsv):
        try:
            with open(input_tsv, 'r', encoding='utf-8') as f:
                # Skip header
                lines = f.readlines()[1:] 
                for line in lines:
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        start_ms = float(parts[0])
                        end_ms = float(parts[1])
                        text = parts[2]
                        transcript_segments.append({
                            'start': start_ms / 1000.0, 
                            'end': end_ms / 1000.0, 
                            'text': text
                        })
        except Exception as e:
            print(f"Error parsing TSV: {e}")

    # Fallback to SRT parser if TSV empty/failed
    if not transcript_segments and os.path.exists(input_srt):
         with open(input_srt, 'r', encoding='utf-8') as f:
             srt_content = f.read()
         pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*)', re.DOTALL)
         matches = pattern.findall(srt_content)
         
         def srt_time_to_seconds(t_str):
             h, m, s = t_str.replace(',', '.').split(':')
             return int(h) * 3600 + int(m) * 60 + float(s)

         for m in matches:
             start_sec = srt_time_to_seconds(m[1])
             end_sec = srt_time_to_seconds(m[2])
             text = m[3].replace('\n', ' ')
             transcript_segments.append({'start': start_sec, 'end': end_sec, 'text': text})

    if not transcript_segments:
        raise ValueError("Could not parse transcript from TSV or SRT.")
    
    return transcript_segments

def process_segments(raw_segments, transcript_segments, min_duration, max_duration, output_count=None):
    """
    Aligns raw AI segments (with reference tags) to actual transcript timestamps.
    Applies constraints, validation, and deduplication.
    """
    
    all_segments = raw_segments
    tempo_minimo = min_duration
    tempo_maximo = max_duration
    
    # Sort segments by score (descending)
    try:
        all_segments.sort(key=lambda x: int(x.get('score', 0)), reverse=True)
    except:
        pass

    # --- POST-PROCESSING: Match Text to Timestamps ---
    processed_segments = []
    
    print(f"[DEBUG] Matching {len(all_segments)} raw segments to timestamps...")
    
    for seg in all_segments:
        try:
            # 1. Parse Reference Time
            ref_time_str = seg.get('start_time_ref', '(0s)')
            ref_time_val = 0
            try:
                if isinstance(ref_time_str, str):
                    match = re.search(r'\d+', ref_time_str)
                    if match:
                         ref_time_val = int(match.group())
                else:
                    ref_time_val = int(ref_time_str)
            except:
                ref_time_val = 0
                
            # Find segment index closest to ref_time
            start_idx = 0
            min_diff = 999999
            for i, s in enumerate(transcript_segments):
                diff = abs(s['start'] - ref_time_val)
                if diff < min_diff:
                    min_diff = diff
                    start_idx = i
                if s['start'] > ref_time_val + 10: 
                    break
            
            # Backtrack
            start_idx = max(0, start_idx - 5)
            
            # 2. Find Exact Start Text
            start_text_target = seg.get('start_text', '').lower().strip()
            # Normalize
            start_text_target = re.sub(r'[^\w\s]', '', start_text_target)
            
            final_start_time = -1
            match_start_idx = -1
            
            # Search window
            search_limit = min(len(transcript_segments), start_idx + 50)
            
            for i in range(start_idx, search_limit):
                s_text = transcript_segments[i]['text'].lower()
                s_text = re.sub(r'[^\w\s]', '', s_text)
                
                # Check for partial match
                if start_text_target and (start_text_target in s_text or s_text in start_text_target):
                    final_start_time = transcript_segments[i]['start']
                    match_start_idx = i
                    break
            
            # Fallback
            if final_start_time == -1:
                final_start_time = transcript_segments[start_idx]['start'] if start_idx < len(transcript_segments) else ref_time_val
                match_start_idx = start_idx

            # 3. Find End Text
            end_text_target = seg.get('end_text', '').lower().strip()
            end_text_target = re.sub(r'[^\w\s]', '', end_text_target)
            
            final_end_time = -1
            
            if match_start_idx != -1:
                search_end_limit = min(len(transcript_segments), match_start_idx + 200)
                
                for i in range(match_start_idx, search_end_limit):
                    s_text = transcript_segments[i]['text'].lower()
                    s_text = re.sub(r'[^\w\s]', '', s_text)
                    
                    if end_text_target and (end_text_target in s_text or s_text in end_text_target):
                         final_end_time = transcript_segments[i]['end']
                         break
            
            # Fallback End Time
            if final_end_time == -1:
                 final_end_time = final_start_time + tempo_minimo 
            
            # Calculate Duration
            duration = final_end_time - final_start_time
            
            # Validate Duration (Min)
            if duration < tempo_minimo: 
                print(f"[WARN] Segment shorter than min duration ({duration:.2f}s < {tempo_minimo}s). Extending to {tempo_minimo}s.")
                duration = tempo_minimo
                final_end_time = final_start_time + duration
            
            # Validate Duration (Max)
            if duration > tempo_maximo:
                print(f"[WARN] Segment exceeds max duration ({duration:.2f}s > {tempo_maximo}s). Cutting to {tempo_maximo}s.")
                final_end_time = final_start_time + tempo_maximo
                duration = tempo_maximo

            # Construct Final Segment
            processed_segments.append({
                "title": seg.get('title', 'Viral Segment'),
                "start_time": final_start_time,
                "end_time": final_end_time,
                "hook": seg.get('title', ''), 
                "reasoning": seg.get('reasoning', ''),
                "score": seg.get('score', 0),
                "duration": duration
            })

        except Exception as e:
            print(f"[WARN] Error processing segment {seg}: {e}")
            continue

    # Deduplication
    unique_segments = []
    processed_segments.sort(key=lambda x: int(x.get('score', 0)), reverse=True)
    
    for candidate in processed_segments:
        is_dup = False
        for existing in unique_segments:
            s1, e1 = candidate['start_time'], candidate['end_time']
            # Simple float equality isn't safe, but max/min handles it
            s2, e2 = existing['start_time'], existing['end_time']
            
            overlap_start = max(s1, s2)
            overlap_end = min(e1, e2)
            
            if overlap_end > overlap_start:
                intersection = overlap_end - overlap_start
                if intersection > 5: # more than 5 seconds overlap
                    is_dup = True
                    print(f"[DEBUG] Dropping overlap: '{candidate.get('title')}' ({s1:.1f}-{e1:.1f}) overlaps with '{existing.get('title')}' ({s2:.1f}-{e2:.1f}) by {intersection:.1f}s")
                    break
        if not is_dup:
            unique_segments.append(candidate)

    all_segments = unique_segments
    print(f"[DEBUG] Finished processing. {len(all_segments)} segments valid.")

    if output_count and len(all_segments) > output_count:
        print(f"Filtering the top {output_count} segments from {len(all_segments)} candidates found in chunks.")
        all_segments = all_segments[:output_count]

    final_result = {"segments": all_segments}
    
    # Basic validation that we have start_time
    validated_segments = []
    for seg in final_result['segments']:
        if 'start_time' in seg:
             validated_segments.append(seg)
    
    final_result['segments'] = validated_segments
    
    return final_result


def _speech_seconds(transcript_segments):
    return sum(max(0.0, float(s.get("end", 0)) - float(s.get("start", 0))) for s in transcript_segments)


def _video_duration(project_folder, transcript_segments=None):
    video = os.path.join(project_folder, "input.mp4")
    if os.path.exists(video):
        try:
            out = subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                text=True,
            )
            value = float(out.strip())
            if value > 0:
                return value
        except Exception as e:
            print(f"[WARN] ffprobe duration failed: {e}")
    if transcript_segments:
        return max((float(s.get("end", 0)) for s in transcript_segments), default=0.0)
    return 0.0


def _fallback_timeline_segments(count, min_duration, max_duration, video_duration):
    count = max(1, int(count or 1))
    if video_duration <= 0:
        return {"segments": []}
    clip_len = min(float(max_duration), max(float(min_duration), 45.0), video_duration)
    pad = min(5.0, video_duration * 0.02)
    usable = max(clip_len, video_duration - pad)
    step = (usable - clip_len) / (count - 1) if count > 1 else 0
    segments = []
    for i in range(count):
        start = pad + i * step if count > 1 else max(0.0, (video_duration - clip_len) / 3.0)
        end = min(video_duration, start + clip_len)
        start = max(0.0, end - clip_len)
        segments.append({
            "title": f"Compilation clip {i + 1}",
            "start_time": start,
            "end_time": end,
            "hook": "Timeline fallback",
            "reasoning": "Low-speech / compilation video: evenly spaced cuts.",
            "score": 60,
            "duration": end - start,
        })
    return {"segments": segments}


def _fallback_visual_segments(project_folder, count, min_duration, max_duration, video_duration):
    try:
        from scripts.visual_segment_selector import select_visual_segments
        return select_visual_segments(
            project_folder,
            count,
            min_duration,
            max_duration,
            video_duration=video_duration,
        )
    except Exception as e:
        print(f"[WARN] Visual scoring failed: {e}. Using evenly spaced timeline cuts.")
        return _fallback_timeline_segments(count, min_duration, max_duration, video_duration)


def create(num_segments, viral_mode, themes, tempo_minimo, tempo_maximo, ai_mode="manual", api_key=None, project_folder="tmp", chunk_size_arg=None, model_name_arg=None):
    quantidade_de_virals = num_segments

    # 1. Load Transcript
    try:
        transcript_segments = load_transcript(project_folder)
    except Exception as e:
        duration = _video_duration(project_folder)
        print(f"[WARN] {e} Using visual selection.")
        return _fallback_visual_segments(project_folder, quantidade_de_virals, tempo_minimo, tempo_maximo, duration)

    # 2. Pre-process Content
    formatted_content = preprocess_transcript_for_ai(transcript_segments)
    content = formatted_content
    speech_sec = _speech_seconds(transcript_segments)
    if speech_sec < float(tempo_minimo):
        duration = _video_duration(project_folder, transcript_segments)
        print(f"[WARN] Transcript has only {speech_sec:.1f}s of speech (< {tempo_minimo}s). Using visual selection.")
        return _fallback_visual_segments(project_folder, quantidade_de_virals, tempo_minimo, tempo_maximo, duration)

    # Load Config and Prompt
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, 'api_config.json')
    prompt_path = os.path.join(base_dir, 'prompt.txt')

    config = {
        "selected_api": "gemini",
        "gemini": {
            "api_key": "",
            "model": "gemini-2.5-flash-lite-preview-09-2025",
            "chunk_size": 15000
        },
        "g4f": {
            "model": "gpt-4o-mini",
            "chunk_size": 2000
        },
        "groq": {
            "api_key": "",
            "model": "openai/gpt-oss-120b",
            "chunk_size": 40000
        },
        "cloudflare": {
            "account_id": "",
            "api_token": "",
            "model": "@cf/openai/gpt-oss-120b",
            "chunk_size": 40000
        }
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                if "gemini" in loaded_config: config["gemini"].update(loaded_config["gemini"])
                if "g4f" in loaded_config: config["g4f"].update(loaded_config["g4f"])
                if "groq" in loaded_config: config["groq"].update(loaded_config["groq"])
                if "cloudflare" in loaded_config: config["cloudflare"].update(loaded_config["cloudflare"])
                if "selected_api" in loaded_config: config["selected_api"] = loaded_config["selected_api"]
        except Exception as e:
            print(f"Error reading api_config.json: {e}")

    # Config Vars
    current_chunk_size = 15000
    model_name = ""
    
    if ai_mode == "gemini":
        cfg_chunk = config["gemini"].get("chunk_size", 15000)
        current_chunk_size = chunk_size_arg if chunk_size_arg and int(chunk_size_arg) > 0 else cfg_chunk
        cfg_model = config["gemini"].get("model", "gemini-2.5-flash-lite-preview-09-2025")
        model_name = model_name_arg if model_name_arg else cfg_model
        if not api_key: api_key = config["gemini"].get("api_key", "")
            
    elif ai_mode == "g4f":
        cfg_chunk = config["g4f"].get("chunk_size", 2000)
        current_chunk_size = chunk_size_arg if chunk_size_arg and int(chunk_size_arg) > 0 else cfg_chunk
        cfg_model = config["g4f"].get("model", "gpt-4o-mini")
        model_name = model_name_arg if model_name_arg else cfg_model

    elif ai_mode == "groq":
        cfg_chunk = config["groq"].get("chunk_size", 40000)
        current_chunk_size = chunk_size_arg if chunk_size_arg and int(chunk_size_arg) > 0 else cfg_chunk
        cfg_model = config["groq"].get("model", "openai/gpt-oss-120b")
        model_name = model_name_arg if model_name_arg else cfg_model
        if not api_key:
            api_key = config["groq"].get("api_key", "")

    elif ai_mode == "cloudflare":
        cfg_chunk = config["cloudflare"].get("chunk_size", 40000)
        current_chunk_size = chunk_size_arg if chunk_size_arg and int(chunk_size_arg) > 0 else cfg_chunk
        cfg_model = config["cloudflare"].get("model", "@cf/openai/gpt-oss-120b")
        model_name = model_name_arg if model_name_arg else cfg_model

    system_prompt_template = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt_template = f.read()
    else:
        print("Warning: prompt.txt not found. Using internal prompt.")
        system_prompt_template = """You are a World-Class Viral Video Editor.
{context_instruction}
Analyze the transcript below with time tags (XXs). Find {amount} viral segments.
Constraints: Each segment MUST be between {min_duration} seconds and {max_duration} seconds.
IMPORTANT: Output "Title", "Hook", and "Reasoning" in the SAME LANGUAGE as the transcript (e.g., if transcript is Portuguese, output Portuguese).
TRANSCRIPT:
{transcript_chunk}
OUTPUT JSON ONLY:
{json_template}"""


    json_template = '''
            { "segments" :
                [
                    {
                        "start_text": "Exact first 5-10 words of the segment",
                        "end_text": "Exact last 5-10 words of the segment",
                        "start_time_ref": "Value of closest (XXs) tag",
                        "title": "Viral Hook Title (Same Language as Transcript)",
                        "reasoning": "Why this is viral? Hook? Value? (Same Language as Transcript)",
                        "score": 95
                    }
                ]
            }
        '''

    # Chunking
    chunk_size = int(current_chunk_size)
    overlap_size = max(1000, int(chunk_size * 0.1))
    
    chunks = []
    start = 0
    content_len = len(content)

    print(f"[DEBUG] Chunking content (Size: {content_len}) with Chunk Size: {chunk_size} and Overlap: {overlap_size}")

    while start < content_len:
        end = min(start + chunk_size, content_len)
        if end < content_len:
            last_space = content.rfind(' ', start, end)
            if last_space != -1 and last_space > start:
                end = last_space
        chunk_text = content[start:end]
        if chunk_text.strip():
            chunks.append(chunk_text)
        if end >= content_len:
            break
        next_start = max(start + 1, end - overlap_size)
        safe_space = content.rfind(' ', start, next_start)
        if safe_space != -1:
            start = safe_space + 1
        else:
            start = next_start

    if viral_mode:
        virality_instruction = f"""analyze the segment for potential virality and identify {quantidade_de_virals} most viral segments from the transcript"""
    else:
        virality_instruction = f"""analyze the segment for potential virality and identify {quantidade_de_virals} the best parts based on the list of themes {themes}."""

    output_texts = []
    for i, chunk in enumerate(chunks):
        context_instruction = ""
        if len(chunks) > 1:
            context_instruction = f"Part {i+1} of {len(chunks)}. "
        
        try:
            prompt = system_prompt_template.format(
                context_instruction=context_instruction,
                virality_instruction=virality_instruction,
                min_duration=tempo_minimo,
                max_duration=tempo_maximo,
                transcript_chunk=chunk,
                json_template=json_template,
                amount=quantidade_de_virals
            )
        except KeyError as e:
            prompt = system_prompt_template
            prompt = prompt.replace("{context_instruction}", context_instruction)
            prompt = prompt.replace("{virality_instruction}", virality_instruction)
            prompt = prompt.replace("{min_duration}", str(tempo_minimo))
            prompt = prompt.replace("{max_duration}", str(tempo_maximo))
            prompt = prompt.replace("{transcript_chunk}", chunk)
            prompt = prompt.replace("{json_template}", json_template)
            prompt = prompt.replace("{amount}", str(quantidade_de_virals))

        output_texts.append(prompt)

    try:
        full_prompt_path = os.path.join(project_folder, "prompt_full.txt")
        full_prompt = system_prompt_template
        full_prompt = full_prompt.replace("{context_instruction}", "Full Video Transcript Analysis")
        full_prompt = full_prompt.replace("{virality_instruction}", virality_instruction)
        full_prompt = full_prompt.replace("{min_duration}", str(tempo_minimo))
        full_prompt = full_prompt.replace("{max_duration}", str(tempo_maximo))
        full_prompt = full_prompt.replace("{transcript_chunk}", content) 
        full_prompt = full_prompt.replace("{json_template}", json_template)
        full_prompt = full_prompt.replace("{amount}", str(quantidade_de_virals))
        
        with open(full_prompt_path, "w", encoding="utf-8") as f:
            f.write(full_prompt)
    except Exception as e:
        print(f"[WARN] Could not save prompt_full.txt: {e}")

    all_raw_segments = []

    print(f"Processing {len(output_texts)} chunks using mode: {ai_mode.upper()}")

    for i, prompt in enumerate(output_texts):
        response_text = ""
        manual_prompt_path = os.path.join(project_folder, f"prompt_part_{i+1}.txt")
        try:
            with open(manual_prompt_path, "w", encoding="utf-8") as f:
                f.write(prompt)
        except Exception as e:
            print(f"[ERROR] Failed to save prompt.txt: {e}")
        
        if ai_mode == "manual":
            print(f"\n[INFO] Prompt saved at: {manual_prompt_path}")
            print("\n" + "="*60)
            print(f"CHUNK {i+1}/{len(output_texts)}")
            print("="*60)
            print("COPY THE PROMPT BELOW (OR FROM THE GENERATED FILE) AND PASTE INTO YOUR PREFERRED AI:")
            print("-" * 20)
            print(prompt)
            print("-" * 20)
            print("="*60)
            print("Paste the response JSON below and press ENTER.")
            print("Tip: If the JSON has multiple lines, try pasting it all at once or minified.")
            print("Alternatively, type 'file' to read from a 'tmp/response.json' file.")
            
            user_input = input("JSON or 'file': ")
            
            if user_input.lower() == 'file':
                try:
                    response_json_path = os.path.join(project_folder, 'response.json')
                    with open(response_json_path, 'r', encoding='utf-8') as rf:
                        response_text = rf.read()
                except FileNotFoundError:
                    print(f"File {response_json_path} not found.")
            else:
                response_text = user_input
                if response_text.strip().startswith("{") and not response_text.strip().endswith("}"):
                    print("Looks incomplete. Paste the rest and press Enter (or Ctrl+C to cancel):")
                    try:
                        rest = sys.stdin.read() 
                        response_text += rest
                    except:
                        pass

        elif ai_mode == "gemini":
            print(f"Sending chunk {i+1} to Gemini (Model: {model_name})...")
            response_text = call_gemini(prompt, api_key, model_name=model_name)
        elif ai_mode == "g4f":
            print(f"Sending chunk {i+1} to G4F (Model: {model_name})...")
            response_text = call_g4f(prompt, model_name=model_name)
        elif ai_mode == "groq":
            print(f"Sending chunk {i+1} to Groq (Model: {model_name})...")
            response_text = call_groq(prompt, api_key, model_name=model_name)
        elif ai_mode == "cloudflare":
            print(f"Sending chunk {i+1} to Cloudflare (Model: {model_name})...")
            cf_cfg = config.get("cloudflare") or {}
            response_text = call_cloudflare(
                prompt,
                cf_cfg.get("account_id", ""),
                cf_cfg.get("api_token", ""),
                model_name=model_name,
            )

        # --- Save RAW Response for Debugging ---
        try:
            raw_response_path = os.path.join(project_folder, f"response_raw_part_{i+1}.txt")
            with open(raw_response_path, "w", encoding="utf-8") as f:
                f.write(response_text)
            print(f"[DEBUG] Raw response saved to: {raw_response_path}")
        except Exception as e:
            print(f"[WARN] Failed to save raw response: {e}")

        # Process response
        try:
            data = clean_json_response(response_text)
            chunk_segments = data.get("segments", [])
            print(f"Found {len(chunk_segments)} segments in this chunk.")
            all_raw_segments.extend(chunk_segments)
        except json.JSONDecodeError:
            print(f"Error: Invalid response.")
        except Exception as e:
            print(f"Unknown error processing chunk: {e}")

    result = process_segments(
        all_raw_segments,
        transcript_segments,
        tempo_minimo,
        tempo_maximo,
        output_count=quantidade_de_virals,
    )
    if result.get("segments"):
        return result
    duration = _video_duration(project_folder, transcript_segments)
    print("[WARN] Model returned 0 speech segments. Using visual selection.")
    return _fallback_visual_segments(project_folder, quantidade_de_virals, tempo_minimo, tempo_maximo, duration)
