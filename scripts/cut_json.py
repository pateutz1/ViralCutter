import json
import os

def process_segments(data, start_time, end_time):
    new_segments = []
    
    for segment in data.get('segments', []):
        seg_start = segment.get('start', 0)
        seg_end = segment.get('end', 0)
        
        # Check intersection
        if seg_end <= start_time or seg_start >= end_time:
            continue
            
        # Calculate overlap
        # Adjust timestamps relative to the cut
        new_seg_start = max(0, seg_start - start_time)
        new_seg_end = min(end_time, seg_end) - start_time
        
        # Filter words if they exist
        new_words = []
        if 'words' in segment:
            for word in segment['words']:
                w_start = word.get('start', 0)
                w_end = word.get('end', 0)
                
                if w_end > start_time and w_start < end_time:
                    new_w_start = max(0, w_start - start_time)
                    new_w_end = min(end_time, w_end) - start_time
                    word_copy = word.copy()
                    word_copy['start'] = new_w_start
                    word_copy['end'] = new_w_end
                    new_words.append(word_copy)
        
        # If words remain or the segment is valid in time
        if new_words or (new_seg_end > new_seg_start):
            new_segment = segment.copy()
            new_segment['start'] = new_seg_start
            new_segment['end'] = new_seg_end
            if 'words' in segment:
                new_segment['words'] = new_words
            new_segments.append(new_segment)
            
    return {'segments': new_segments}

def cut_json_transcript(input_json_path, output_json_path, start_time, end_time):
    """
    Read input.json (WhisperX), cut the range, and save to output_json_path with adjusted timestamps.
    """
    if not os.path.exists(input_json_path):
        print(f"Warning: {input_json_path} not found. Could not generate cut JSON.")
        return

    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        new_data = process_segments(data, start_time, end_time)
        
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
            
        print(f"Subtitle JSON generated: {output_json_path}")
        
    except Exception as e:
        print(f"Error cutting JSON: {e}")
