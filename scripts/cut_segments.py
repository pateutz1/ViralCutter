from scripts import cut_json
import os
import subprocess
import json

def _encoder_works(encoder, preset):
    """Return True only when FFmpeg can actually initialize the encoder."""
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.1",
        "-frames:v", "1", "-an",
        "-c:v", encoder, "-preset", preset,
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except OSError:
        return False

def _validated_source_ranges(segment):
    ranges = []
    for source in segment.get("source_ranges") or []:
        try:
            start = float(source["start_time"])
            duration = float(source["duration"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"Invalid Text Safe source range: {source!r}")
        if start < 0 or duration <= 0:
            raise ValueError(f"Invalid Text Safe source range: {source!r}")
        ranges.append({"start_time": start, "duration": duration})
    return ranges


def _input_has_audio(input_file):
    command = [
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=index", "-of", "csv=p=0", input_file,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode == 0 and bool(result.stdout.strip())


def _build_montage_command(input_file, output_path, source_ranges, codec, has_audio=True):
    filters = []
    concat_inputs = []
    for index, source in enumerate(source_ranges):
        start = source["start_time"]
        duration = source["duration"]
        filters.append(
            f"[0:v]trim=start={start:.6f}:duration={duration:.6f},"
            f"setpts=PTS-STARTPTS[v{index}]"
        )
        concat_inputs.append(f"[v{index}]")
        if has_audio:
            filters.append(
                f"[0:a]atrim=start={start:.6f}:duration={duration:.6f},"
                f"asetpts=PTS-STARTPTS[a{index}]"
            )
            concat_inputs.append(f"[a{index}]")

    filters.append(
        "".join(concat_inputs)
        + f"concat=n={len(source_ranges)}:v=1:a={1 if has_audio else 0}"
        + ("[vout][aout]" if has_audio else "[vout]")
    )
    command = [
        "ffmpeg", "-y", "-loglevel", "error", "-hide_banner", "-i", input_file,
        "-filter_complex", ";".join(filters), "-map", "[vout]", "-c:v", codec,
    ]
    if codec == "h264_nvenc":
        command.extend(["-preset", "p1", "-b:v", "5M"])
    else:
        command.extend(["-preset", "ultrafast", "-crf", "23"])
    if has_audio:
        command.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "128k"])
    else:
        command.append("-an")
    total_duration = sum(source["duration"] for source in source_ranges)
    command.extend(["-t", f"{total_duration:.6f}", "-movflags", "+faststart", output_path])
    return command

def _parse_seconds(value, treat_large_numbers_as_ms=False):
    """Parse seconds or HH:MM:SS without corrupting legitimate long-video timestamps."""
    if isinstance(value, bool):
        raise ValueError(f"Invalid time value: {value!r}")
    if isinstance(value, (int, float)):
        seconds = float(value)
    else:
        text_value = str(value).strip()
        try:
            seconds = float(text_value)
        except ValueError:
            parts = text_value.split(":")
            if len(parts) == 3:
                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                seconds = int(parts[0]) * 60 + float(parts[1])
            else:
                raise ValueError(f"Invalid time format: {value!r}")
    if treat_large_numbers_as_ms and seconds >= 100000:
        seconds /= 1000.0
    if seconds < 0:
        raise ValueError(f"Time cannot be negative: {value!r}")
    return seconds

def cut(segments, project_folder="tmp", skip_video=False):

    def check_nvenc_support():
        return _encoder_works("h264_nvenc", "p1")

    def generate_segments(response, project_folder, skip_video):
        if not check_nvenc_support():
            print("NVENC is not supported on this system. Falling back to libx264.")
            video_codec = "libx264"
        else:
            video_codec = "h264_nvenc"

        # Look for input.mp4 in project_folder or tmp
        input_file = os.path.join(project_folder, "input.mp4")
        if not os.path.exists(input_file):
            # Try legacy fallback
            input_file_legacy = os.path.join(project_folder, "input_video.mp4")
            if os.path.exists(input_file_legacy):
                input_file = input_file_legacy
            else:
                print(f"Input file not found in {project_folder}")
                return

        # Output folder for cuts
        cuts_folder = os.path.join(project_folder, "cuts")
        os.makedirs(cuts_folder, exist_ok=True)
        
        # Output folder for cut subtitle JSONs
        subs_folder = os.path.join(project_folder, "subs")
        os.makedirs(subs_folder, exist_ok=True)

        # Input JSON (original transcription)
        input_json_path = os.path.join(project_folder, "input.json")

        segments = response.get("segments", [])
        for i, segment in enumerate(segments):
            start_time = segment.get("start_time", "00:00:00")
            duration = segment.get("duration", 0)
            source_ranges = _validated_source_ranges(segment)

            try:
                duration_seconds = _parse_seconds(duration, treat_large_numbers_as_ms=True)
                start_time_seconds = _parse_seconds(start_time, treat_large_numbers_as_ms=True)
            except (TypeError, ValueError) as error:
                print(f"Warning: invalid timing for segment {i}: {error}. Skipping.")
                continue
            if duration_seconds <= 0:
                print(f"Warning: duration <= 0 for segment {i}. Skipping.")
                continue
            duration_str = f"{duration_seconds:.3f}"
            start_time_str = f"{start_time_seconds:.3f}"
            # Title for filename
            title = segment.get("title", f"Segment_{i}")
            safe_title = "".join([c for c in title if c.isalnum() or c in " _-"]).strip()
            safe_title = safe_title.replace(" ", "_")[:60]
            base_name = f"{i:03d}_{safe_title}"

            output_filename = f"{base_name}_original_scale.mp4"
            output_path = os.path.join(cuts_folder, output_filename)

            print(f"Processing segment {i+1}/{len(segments)}")
            print(f"Start time: {start_time}, Duration: {duration}")
            if source_ranges:
                print(f"Text Safe montage: {len(source_ranges)} clean source range(s)")
            # print(f"Executing command: {' '.join(command)}")

            # VIDEO GENERATION
            if not skip_video:
                montage_has_audio = _input_has_audio(input_file) if source_ranges else False

                def build_command(codec):
                    if source_ranges:
                        return _build_montage_command(
                            input_file,
                            output_path,
                            source_ranges,
                            codec,
                            has_audio=montage_has_audio,
                        )
                    command = [
                        "ffmpeg", "-y", "-loglevel", "error", "-hide_banner",
                        "-ss", start_time_str, "-i", input_file,
                        "-t", duration_str, "-c:v", codec,
                    ]
                    if codec == "h264_nvenc":
                        command.extend(["-preset", "p1", "-b:v", "5M"])
                    else:
                        command.extend(["-preset", "ultrafast", "-crf", "23"])
                    command.extend(["-c:a", "aac", "-b:a", "128k", output_path])
                    return command

                codecs_to_try = [video_codec]
                if video_codec != "libx264":
                    codecs_to_try.append("libx264")

                last_error = None
                for codec in codecs_to_try:
                    try:
                        subprocess.run(
                            build_command(codec), check=True,
                            capture_output=True, text=True,
                        )
                        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                            raise RuntimeError(f"FFmpeg created an empty output: {output_path}")
                        print(f"Generated segment with {codec}: {output_filename}, Size: {os.path.getsize(output_path)} bytes")
                        last_error = None
                        break
                    except (subprocess.CalledProcessError, RuntimeError) as error:
                        last_error = error
                        if os.path.exists(output_path):
                            os.remove(output_path)
                        if codec != "libx264":
                            print(f"Encoder {codec} failed. Retrying with CPU (libx264)...")

                if last_error is not None:
                    stderr = getattr(last_error, "stderr", "") or ""
                    raise RuntimeError(f"FFmpeg failed to generate {output_filename}: {stderr.strip()}") from last_error
            else:
                print(f"Skipping video generation for {output_filename} (using existing). check json...")
            
            # --- JSON CUTTING (ALWAYS RUN) ---
            end_time_seconds = start_time_seconds + float(duration_seconds)
            
            # JSON name matching the FINAL video with title
            json_output_filename = f"{base_name}_processed.json"
            json_output_path = os.path.join(subs_folder, json_output_filename)
            
            if source_ranges:
                cut_json.cut_json_transcript_ranges(input_json_path, json_output_path, source_ranges)
            else:
                cut_json.cut_json_transcript(input_json_path, json_output_path, start_time_seconds, end_time_seconds)
            # --------------------

            print("\n" + "="*50 + "\n")

    # Reading the JSON file if segments not provided (legacy behavior)
    if segments is None:
        json_path = os.path.join(project_folder, 'viral_segments.txt')
        with open(json_path, 'r', encoding='utf-8') as file:
            response = json.load(file)
    else:
        response = segments

    generate_segments(response, project_folder, skip_video)
