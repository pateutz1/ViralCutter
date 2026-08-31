import cv2
import mediapipe as mp
import numpy as np
from scripts.content_bounds import normalize_content_bounds

def crop_and_maintain_ar(frame, face_box, target_w, target_h, zoom_out_factor=2.2, content_bounds=None):
    """
    Crop a region based on the face while keeping the target aspect ratio.
    Prevents deformation (stretching/squeezing).
    """
    img_h, img_w, _ = frame.shape
    content_left, content_right = normalize_content_bounds(img_w, content_bounds)
    content_width = content_right - content_left
    x, y, w, h = face_box
    
    # Face center
    cx = x + w // 2
    cy = y + h // 2
    
    # Base face dimension (larger side to ensure coverage)
    face_size = max(w, h)
    
    # Desired crop height (face height * zoom-out factor)
    # zoom_out_factor: larger means more zoomed out (more scenery)
    req_h = face_size * zoom_out_factor
    
    # Target Aspect Ratio (1080 / 960 = 1.125)
    target_ar = target_w / target_h
    
    # Calculate crop width and height keeping AR
    crop_h = req_h
    crop_w = crop_h * target_ar
    
    # Check original image limits (we cannot crop more than exists)
    # If required width is larger than the image, limit by width
    if crop_w > content_width:
        crop_w = float(content_width)
        crop_h = crop_w / target_ar
        
    # If required height is larger than the image, limit by height
    if crop_h > img_h:
        crop_h = float(img_h)
        crop_w = crop_h * target_ar
        
    # Convert to integers
    crop_w = int(crop_w)
    crop_h = int(crop_h)
    
    # Calculate top-left crop coordinates centered on the face
    x1 = int(cx - crop_w // 2)
    y1 = int(cy - crop_h // 2)
    
    # Edge clamp by sliding the window if possible
    # If it goes past the left, snap to the left
    if x1 < content_left:
        x1 = content_left
    # If it goes past the right, snap to the right
    elif x1 + crop_w > content_right:
        x1 = content_right - crop_w
        
    # If it goes past the top
    if y1 < 0: 
        y1 = 0
    # If it goes past the bottom
    elif y1 + crop_h > img_h: 
        y1 = img_h - crop_h
    
    # Final safety check if the image is smaller than the crop (logic above should avoid this)
    x2 = x1 + crop_w
    y2 = y1 + crop_h
    
    # Crop
    cropped = frame[y1:y2, x1:x2]
    
    # If crop fails (size 0), return black
    if cropped.size == 0 or cropped.shape[0] == 0 or cropped.shape[1] == 0:
        return np.zeros((target_h, target_w, 3), dtype=np.uint8)

    # Resize to the final target size (1080x960)
    # Since we kept AR, resize preserves the correct proportion
    resized = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
    return resized

def crop_and_resize_two_faces(frame, face_positions, zoom_out_factor=2.2, content_bounds=None):
    """
    Crop and resize two detected faces in the frame, adjusting for a vertical composition
    1080x1920 where each face occupies half the screen (1080x960).
    """
    # Target dimensions for each half
    target_w = 1080
    target_h = 960
    
    # If we do not have 2 faces, fallback (safety)
    if len(face_positions) < 2:
        return np.zeros((1920, 1080, 3), dtype=np.uint8)

    # First face (Top)
    face1_img = crop_and_maintain_ar(frame, face_positions[0], target_w, target_h, zoom_out_factor, content_bounds)
    
    # Second face (Bottom)
    face2_img = crop_and_maintain_ar(frame, face_positions[1], target_w, target_h, zoom_out_factor, content_bounds)
    
    # Compose final image (Vertical Stack)
    result_frame = np.vstack((face1_img, face2_img))
    
    return result_frame


def detect_face_or_body_two_faces(frame, face_detection, face_mesh, pose):
    # Convert the image to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process face detection
    results_face_detection = face_detection.process(frame_rgb)
    results_face_mesh = face_mesh.process(frame_rgb)
    results_pose = pose.process(frame_rgb)

    face_positions_detection = []
    if results_face_detection.detections:
        for detection in results_face_detection.detections[:2]:
            bbox = detection.location_data.relative_bounding_box
            x_min = int(bbox.xmin * frame.shape[1])
            y_min = int(bbox.ymin * frame.shape[0])
            width = int(bbox.width * frame.shape[1])
            height = int(bbox.height * frame.shape[0])
            face_positions_detection.append((x_min, y_min, width, height))

    if len(face_positions_detection) == 2:
        return face_positions_detection

    face_positions_mesh = []
    if results_face_mesh.multi_face_landmarks:
        for landmarks in results_face_mesh.multi_face_landmarks[:2]:
            x_coords = [int(landmark.x * frame.shape[1]) for landmark in landmarks.landmark]
            y_coords = [int(landmark.y * frame.shape[0]) for landmark in landmarks.landmark]
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)
            width = x_max - x_min
            height = y_max - y_min
            face_positions_mesh.append((x_min, y_min, width, height))

    if len(face_positions_mesh) == 2:
        return face_positions_mesh
        
    # If neither found 2, return what we found (prefer detection as it is bounding box optimized)
    if face_positions_detection:
        return face_positions_detection
    if face_positions_mesh:
        return face_positions_mesh

    # If no face is detected, use pose to estimate the body
    if results_pose.pose_landmarks:
        x_coords = [lmk.x for lmk in results_pose.pose_landmarks.landmark]
        y_coords = [lmk.y for lmk in results_pose.pose_landmarks.landmark]
        x_min = int(min(x_coords) * frame.shape[1])
        x_max = int(max(x_coords) * frame.shape[1])
        y_min = int(min(y_coords) * frame.shape[0])
        y_max = int(max(y_coords) * frame.shape[0])
        width = x_max - x_min
        height = y_max - y_min
        return [(x_min, y_min, width, height)]

    return None
