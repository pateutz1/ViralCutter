import os
import json
import tempfile


def _write_json_atomically(output_path, data):
    output_dir = os.path.dirname(output_path) or "."
    fd, temporary_path = tempfile.mkstemp(prefix=".viral_segments_", suffix=".tmp", dir=output_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        os.replace(temporary_path, output_path)
    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise

def save_viral_segments(segments_data=None, project_folder="tmp"):
    output_txt_file = os.path.join(project_folder, "viral_segments.txt")

    if segments_data is not None:
        _write_json_atomically(output_txt_file, segments_data)
        print(f"Viral segments saved to {output_txt_file}\n")
        return

    # Check if the file already exists
    if not os.path.exists(output_txt_file):
        # Ask the user to enter JSON if the file does not exist and segments are not defined
        while True:
            user_input = input("\nPlease enter the JSON in the desired format:\n")
            try:
                segments_data = json.loads(user_input)
                if "segments" in segments_data and isinstance(segments_data["segments"], list):
                    _write_json_atomically(output_txt_file, segments_data)
                    print(f"Viral segments saved to {output_txt_file}")
                    break
                print("Invalid format. Make sure the structure is correct.")
            except json.JSONDecodeError:
                print("Error decoding JSON. Please check the formatting.")
            print("Please try again.")
    else:
        print(f"The file {output_txt_file} already exists. No additional input is needed.")
