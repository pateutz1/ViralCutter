import os
import subprocess
import sys

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def burn_video_file(video_path, subtitle_path, output_path):
    """
    Burns subtitles into a single video file.
    """
    # Adjust subtitle path for FFmpeg (Forward Slash and escape of :)
    # On Windows, "C:/foo" works if wrapped in single quotes inside the filter.
    # To be safe, we use replace and forward slashes.
    subtitle_file_ffmpeg = subtitle_path.replace('\\', '/').replace(':', '\\:')

    def run_ffmpeg(encoder, preset, additional_args=[]):
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error", "-hide_banner",
            '-i', video_path,
            '-vf', f"subtitles='{subtitle_file_ffmpeg}'",
            '-c:v', encoder,
            '-preset', preset,
            '-b:v', '5M',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'copy',
            output_path
        ] + additional_args
        subprocess.run(cmd, check=True, capture_output=True)

    # Try NVENC first
    try:
        # print(f"Processing video (NVENC): {os.path.basename(video_path)}")
        run_ffmpeg("h264_nvenc", "p1")
        # print(f"Processed: {output_path}")
        return True, "NVENC Success"
    except subprocess.CalledProcessError as e:
        print(f"Error with NVENC ({str(e)}). Trying CPU (libx264)...")
        try:
            # Fallback CPU
            run_ffmpeg("libx264", "ultrafast")
            # print(f"Processed (CPU): {output_path}")
            return True, "CPU Success"
        except subprocess.CalledProcessError as e2:
            err_msg = f"FATAL ERROR burning subtitles into {os.path.basename(video_path)}: {e2}"
            if e2.stderr:
                 err_msg += f" | FFmpeg Log: {e2.stderr.decode('utf-8')}"
            print(err_msg)
            return False, err_msg
    except Exception as e:
        return False, str(e)

def burn(project_folder="tmp"):
    # Convert to absolute to avoid errors in the ffmpeg filter
    if project_folder and not os.path.isabs(project_folder):
        project_folder_abs = os.path.abspath(project_folder)
    else:
        project_folder_abs = project_folder

    # Folder paths
    subs_folder = os.path.join(project_folder_abs, 'subs_ass')
    videos_folder = os.path.join(project_folder_abs, 'final')
    output_folder = os.path.join(project_folder_abs, 'burned_sub')  # Folder to save videos with subtitles

    # Create output folder if it does not exist
    os.makedirs(output_folder, exist_ok=True)
    
    if not os.path.exists(videos_folder):
        print(f"Final videos folder not found: {videos_folder}")
        return

    # Iterate over video files in the final folder
    files = os.listdir(videos_folder)
    if not files:
        print("No files found in 'final' to burn subtitles.")
        return

    for video_file in files:
        if video_file.endswith(('.mp4', '.mkv', '.avi')):  # Supported formats
            # If it is a temp file (e.g. temp_video_no_audio), skip if the final version exists
            if "temp_video_no_audio" in video_file:
                continue

            # Extract the video base name (without extension)
            video_name = os.path.splitext(video_file)[0]
            
            # Define the path for the matching subtitle
            subtitle_file = os.path.join(subs_folder, f"{video_name}.ass")
            
            # Also try with _processed suffix in case the convention differs
            if not os.path.exists(subtitle_file):
                subtitle_file_processed = os.path.join(subs_folder, f"{video_name}_processed.ass")
                if os.path.exists(subtitle_file_processed):
                    subtitle_file = subtitle_file_processed
            
            # Check if the subtitle exists
            if os.path.exists(subtitle_file):
                # Define the output path for the video with subtitles
                output_file = os.path.join(output_folder, f"{video_name}_subtitled.mp4")

                print(f"Burning: {video_name}...")
                success, msg = burn_video_file(os.path.join(videos_folder, video_file), subtitle_file, output_file)
                if success:
                    print(f"Done: {output_file}")
                else:
                    print(f"Fail: {msg}")
            else:
                print(f"Subtitle not found for: {video_name} at {subtitle_file}")
