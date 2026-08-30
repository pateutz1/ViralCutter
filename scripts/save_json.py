import os
import json

def save_viral_segments(segments_data=None, project_folder="tmp"):
    output_txt_file = os.path.join(project_folder, "viral_segments.txt")

    # Check if the file already exists
    if not os.path.exists(output_txt_file):
        if segments_data is None:
            # Ask the user to enter JSON if the file does not exist and segments are not defined
            while True:
                user_input = input("\nPlease enter the JSON in the desired format:\n")
                try:
                    # Try loading the entered JSON
                    segments_data = json.loads(user_input)

                    # Validate that the format is correct
                    if "segments" in segments_data and isinstance(segments_data["segments"], list):
                        # Save the data to a JSON file
                        with open(output_txt_file, 'w', encoding='utf-8') as file:
                            json.dump(segments_data, file, ensure_ascii=False, indent=4)
                        print(f"Viral segments saved to {output_txt_file}")
                        break
                    else:
                        print("Invalid format. Make sure the structure is correct.")
                except json.JSONDecodeError:
                    print("Error decoding JSON. Please check the formatting.")
                print("Please try again.")
        else:
            # If segments were generated, save automatically
            with open(output_txt_file, 'w', encoding='utf-8') as file:
                json.dump(segments_data, file, ensure_ascii=False, indent=4)
            print(f"Viral segments saved to {output_txt_file}\n")
    else:
        print(f"The file {output_txt_file} already exists. No additional input is needed.")
