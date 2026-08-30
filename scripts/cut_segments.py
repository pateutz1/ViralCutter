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

            # Heuristic for duration:
            if isinstance(duration, (int, float)):
                if duration < 1000:
                    duration_seconds = float(duration)
                else:
                    duration_seconds = duration / 1000.0
                duration_str = f"{duration_seconds:.3f}"
            else:
                # Try converting string (HH:MM:SS or float str)
                try:
                    duration_seconds = float(duration)
                    duration_str = f"{duration_seconds:.3f}"
                except ValueError:
                    # Assume hh:mm:ss format if not float
                     # Implement parser if needed, but assume float for now based on history
                    duration_seconds = 0
                    duration_str = duration
            
            # Heuristic for start_time:
            if isinstance(start_time, (int, float)):
                if start_time > 10000: # Large milliseconds? Assuming seconds or HHMMSS?
                   # Original code: if start_time int -> start_time/1000.0.
                   # Keep the original logic: int -> milliseconds
                   pass
            
            # Redoing the exact original logic for safety and capturing the float:
            if isinstance(start_time, int):
                start_time_seconds = start_time / 1000.0
                start_time_str = f"{start_time_seconds:.3f}"
            elif isinstance(start_time, float):
                 start_time_seconds = start_time
                 start_time_str = f"{start_time_seconds:.3f}"
            else:
                # String "00:00:00" or "12.34"
                try:
                    start_time_seconds = float(start_time)
                    start_time_str = f"{start_time_seconds:.3f}"
                except:
                    # If HH:MM:SS, ffmpeg accepts it, but we need float for the json cutter
                    # Simple helper
                    h, m, s = str(start_time).split(':')
                    start_time_seconds = int(h) * 3600 + int(m) * 60 + float(s)
                    start_time_str = str(start_time)

            # Title for filename
            title = segment.get("title", f"Segment_{i}")
            safe_title = "".join([c for c in title if c.isalnum() or c in " _-"]).strip()
            safe_title = safe_title.replace(" ", "_")[:60]
            base_name = f"{i:03d}_{safe_title}"

            output_filename = f"{base_name}_original_scale.mp4"
            output_path = os.path.join(cuts_folder, output_filename)

            print(f"Processing segment {i+1}/{len(segments)}")
            print(f"Start time: {start_time}, Duration: {duration}")
            # print(f"Executing command: {' '.join(command)}")

            # VIDEO GENERATION
            if not skip_video:
                def build_command(codec):
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
