import cv2
import numpy as np
import os
import subprocess
import mediapipe as mp

def crop_and_resize_single_face(frame, face):
        frame_height, frame_width = frame.shape[:2]

        x, y, w, h = face
        face_center_x = x + w // 2
        face_center_y = y + h // 2

        # Calculate desired aspect ratio (9:16)
        target_aspect_ratio = 9 / 16

        # Calculate crop area to avoid black bars
        if frame_width / frame_height > target_aspect_ratio:
            new_width = int(frame_height * target_aspect_ratio)
            new_height = frame_height
        else:
            new_width = frame_width
            new_height = int(frame_width / target_aspect_ratio)

        # Ensure the crop stays within bounds
        crop_x = max(0, min(face_center_x - new_width // 2, frame_width - new_width))
        crop_y = max(0, min(face_center_y - new_height // 2, frame_height - new_height))
        crop_x2 = crop_x + new_width
        crop_y2 = crop_y + new_height

        # Crop and resize to 1080x1920 (9:16)
        crop_img = frame[crop_y:crop_y2, crop_x:crop_x2]
        resized = cv2.resize(crop_img, (1080, 1920), interpolation=cv2.INTER_AREA)

        return resized

def resize_with_padding(frame):
        frame_height, frame_width = frame.shape[:2]
        target_aspect_ratio = 9 / 16

        if frame_width / frame_height > target_aspect_ratio:
            new_width = frame_width
            new_height = int(frame_width / target_aspect_ratio)
        else:
            new_height = frame_height
            new_width = int(frame_height * target_aspect_ratio)

        # Create a black canvas
        result = np.zeros((new_height, new_width, 3), dtype=np.uint8)

        # Calculate margins
        pad_top = (new_height - frame_height) // 2
        pad_left = (new_width - frame_width) // 2

        # Place the original frame on the canvas
        result[pad_top:pad_top+frame_height, pad_left:pad_left+frame_width] = frame

        # Resize to final dimensions
        return cv2.resize(result, (1080, 1920), interpolation=cv2.INTER_AREA)

def detect_face_or_body(frame, face_detection, face_mesh, pose):
    # Convert the image to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process face detection
    results_face_detection = face_detection.process(frame_rgb)
    results_face_mesh = face_mesh.process(frame_rgb)
    results_pose = pose.process(frame_rgb)

    detections = []

    # Use face detection if available
    if results_face_detection.detections:
        # Use the first detected face
        detection = results_face_detection.detections[0]
        bbox = detection.location_data.relative_bounding_box
        x_min = int(bbox.xmin * frame.shape[1])
        y_min = int(bbox.ymin * frame.shape[0])
        width = int(bbox.width * frame.shape[1])
        height = int(bbox.height * frame.shape[0])
        detections.append((x_min, y_min, width, height))
    
    # Use face mesh landmarks if available
    if results_face_mesh.multi_face_landmarks:
        landmarks = results_face_mesh.multi_face_landmarks[0].landmark
        # Face coordinates based on key points (landmarks)
        x_coords = [int(landmark.x * frame.shape[1]) for landmark in landmarks]
        y_coords = [int(landmark.y * frame.shape[0]) for landmark in landmarks]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        width = x_max - x_min
        height = y_max - y_min
        detections.append((x_min, y_min, width, height))

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
        detections.append((x_min, y_min, width, height))

    # If nothing is detected, return an empty list
    return detections if detections else None


def crop_center_zoom(frame):
    """
    Crops the center of the frame to fill 9:16 aspect ratio (Zoom effect).
    """
    frame_height, frame_width = frame.shape[:2]
    target_aspect_ratio = 9 / 16
    
    # Calculate crop dimensions to FILL the target ratio
    if frame_width / frame_height > target_aspect_ratio:
        # Source is wider than target (e.g. 16:9 source, 9:16 target) -> Crop Width
        new_width = int(frame_height * target_aspect_ratio)
        new_height = frame_height
    else:
        # Source is taller than target -> Crop Height
        new_width = frame_width
        new_height = int(frame_width / target_aspect_ratio)
        
    start_x = (frame_width - new_width) // 2
    start_y = (frame_height - new_height) // 2
    
    # Ensure bounds
    start_x = max(0, start_x)
    start_y = max(0, start_y)
    
    crop_img = frame[start_y:start_y+new_height, start_x:start_x+new_width]
    
    # Resize to final 1080x1920
    return cv2.resize(crop_img, (1080, 1920), interpolation=cv2.INTER_AREA)

