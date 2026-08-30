import os
import json
import shutil
import re
from i18n.i18n import I18nAuto

i18n = I18nAuto()

def sanitize_filename(name):
    """Remove invalid characters for file/folder names."""
    # Remove invalid characters such as / \ : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    # Remove extra spaces and line breaks
    cleaned = cleaned.strip()
    return cleaned

def organize():
    print(i18n("Organizing output files..."))
    
    # Paths
    meta_path = "tmp/viral_segments.txt"
    burned_folder = "burned_sub"
    virals_root = "VIRALS"
    
    if not os.path.exists(meta_path):
        print(i18n("Metadata file not found: ") + meta_path)
        return
        
    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            segments = data.get("segments", [])
    except Exception as e:
        print(i18n("Error reading metadata: ") + str(e))
        return

    os.makedirs(virals_root, exist_ok=True)
    
    processed_count = 0
    
    for i, segment in enumerate(segments):
        title = segment.get("title", f"Viral_Segment_{i+1}")
        clean_title = sanitize_filename(title)
        
        # If the title is empty after sanitization, use fallback
        if not clean_title:
            clean_title = f"Viral_Segment_{i+1}"
            
        # Create viral folder
        viral_folder = os.path.join(virals_root, clean_title)
        os.makedirs(viral_folder, exist_ok=True)
        
        # Identify the final video file
        # Expected pattern: outputXXX_original_scale_subtitled.mp4
        # The pattern may vary depending on how burn_subtitles was run, but usually follows the index
        # Try locating by index pattern
        
        video_filename_pattern = f"output{str(i).zfill(3)}_original_scale_subtitled.mp4"
        source_video = os.path.join(burned_folder, video_filename_pattern)
        
        # If not found with subtitled, try without (in case burn was skipped?)
        if not os.path.exists(source_video):
            # Try the 'final' folder if there is no burned subtitle
            source_video_final = os.path.join("final", f"output{str(i).zfill(3)}_original_scale.mp4")
            if os.path.exists(source_video_final):
                source_video = source_video_final
            else:
                # Try pattern without 'original_scale' or other variations if needed
                print(i18n(f"Warning: Could not find video file for segment {i+1} ({title})"))
                continue
                
        # Define final paths
        target_video = os.path.join(viral_folder, f"{clean_title}.mp4")
        target_json = os.path.join(viral_folder, f"{clean_title}.json")
        
        # Move/Copy Video
        try:
            shutil.copy2(source_video, target_video)
        except Exception as e:
            print(i18n(f"Error copying video for segment {i}: {e}"))
            continue
            
        # Save individual JSON
        try:
            with open(target_json, 'w', encoding='utf-8') as f:
                json.dump(segment, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(i18n(f"Error saving JSON for segment {i}: {e}"))
            
        processed_count += 1
        print(i18n(f"Saved: {clean_title}"))

    print(i18n(f"Organization completed. {processed_count} virals saved in '{virals_root}' folder."))

if __name__ == "__main__":
    organize()
