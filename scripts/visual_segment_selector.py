import math
import os
import subprocess


def _robust_normalize(values, np):
    array = np.asarray(values, dtype=np.float32)
    if array.size == 0:
        return array
    finite = np.isfinite(array)
    if not finite.any():
        return np.zeros_like(array)
    array = np.where(finite, array, 0.0)
    low = float(np.percentile(array, 10))
    high = float(np.percentile(array, 90))
    if high - low < 1e-6:
        return np.zeros_like(array)
    return np.clip((array - low) / (high - low), 0.0, 1.0)


def _rank_windows(sample_times, activity_scores, clip_len, video_duration, count, np, pad=None, stride=None):
    """Rank fixed-length windows and return non-overlapping selections."""
    times = np.asarray(sample_times, dtype=np.float32)
    scores = np.asarray(activity_scores, dtype=np.float32)
    if times.size == 0 or scores.size != times.size or clip_len <= 0:
        return []

    max_start = max(0.0, float(video_duration) - float(clip_len))
    if pad is None:
        pad = min(30.0, max(5.0, float(video_duration) * 0.02))
    first_start = min(float(pad), max_start)
    last_start = max(first_start, max_start - float(pad))
    if stride is None:
        stride = max(5.0, min(15.0, float(clip_len) / 6.0))

    starts = list(np.arange(first_start, last_start + 0.001, stride, dtype=np.float32))
    if not starts or abs(float(starts[-1]) - last_start) > 0.5:
        starts.append(last_start)

    event_threshold = float(np.percentile(scores, 75))
    candidates = []
    for start in starts:
        start = float(start)
        end = min(float(video_duration), start + float(clip_len))
        mask = (times >= start) & (times < end)
        window = scores[mask]
        if window.size < 2:
            continue
        mean_score = float(window.mean())
        peak_score = float(np.percentile(window, 85))
        event_density = float((window >= event_threshold).mean())
        score = 0.55 * mean_score + 0.30 * peak_score + 0.15 * event_density
        candidates.append({"start": start, "end": end, "score": score})

    candidates.sort(key=lambda item: item["score"], reverse=True)
    selected = []
    for candidate in candidates:
        if any(
            min(candidate["end"], current["end"]) - max(candidate["start"], current["start"]) > 5.0
            for current in selected
        ):
            continue
        selected.append(candidate)
        if len(selected) >= max(1, int(count or 1)):
            break
    return selected


def _sample_visual_activity(video_path, video_duration, sample_interval, cv2, np):
    times = []
    motions = []
    scene_changes = []
    sharpness = []
    exposure_quality = []
    previous_gray = None
    previous_hist = None

    width, height = 160, 90
    frame_size = width * height
    fps_filter = 1.0 / float(sample_interval)
    command = [
        "ffmpeg", "-v", "error", "-i", video_path,
        "-vf", f"fps={fps_filter:.8f},scale={width}:{height},format=gray",
        "-an", "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    result = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"FFmpeg visual sampling failed: {error}")

    frame_count = len(result.stdout) // frame_size
    if frame_count < 2:
        raise RuntimeError("Not enough decodable frames for visual scoring")

    frames = np.frombuffer(result.stdout[:frame_count * frame_size], dtype=np.uint8)
    frames = frames.reshape(frame_count, height, width)
    for frame_index, gray in enumerate(frames):
        hist = cv2.calcHist([gray], [0], None, [32], [0, 256])
        cv2.normalize(hist, hist, alpha=1.0, norm_type=cv2.NORM_L1)

        motion = 0.0 if previous_gray is None else float(cv2.absdiff(gray, previous_gray).mean())
        scene = 0.0 if previous_hist is None else float(
            cv2.compareHist(previous_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
        )
        focus = math.log1p(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        brightness = float(gray.mean())
        exposure = max(0.0, 1.0 - abs(brightness - 127.5) / 127.5)

        times.append(frame_index * float(sample_interval))
        motions.append(motion)
        scene_changes.append(scene)
        sharpness.append(focus)
        exposure_quality.append(exposure)
        previous_gray = gray
        previous_hist = hist

    if len(times) < 2:
        raise RuntimeError("Not enough decodable frames for visual scoring")

    visual = (
        0.45 * _robust_normalize(motions, np)
        + 0.25 * _robust_normalize(scene_changes, np)
        + 0.20 * _robust_normalize(sharpness, np)
        + 0.10 * np.asarray(exposure_quality, dtype=np.float32)
    )
    return np.asarray(times, dtype=np.float32), visual


def _sample_audio_activity(video_path, sample_times, sample_interval, np):
    sample_rate = 8000
    command = [
        "ffmpeg", "-v", "error", "-i", video_path,
        "-vn", "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "-",
    ]
    result = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0 or not result.stdout:
        return np.zeros(len(sample_times), dtype=np.float32)

    audio = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32)
    samples_per_bin = max(1, int(sample_rate * sample_interval))
    energies = []
    for offset in range(0, len(audio), samples_per_bin):
        chunk = audio[offset:offset + samples_per_bin]
        energies.append(float(np.sqrt(np.mean(chunk * chunk))) if chunk.size else 0.0)
    energy = _robust_normalize(np.log1p(energies), np)
    energy_times = np.arange(len(energy), dtype=np.float32) * float(sample_interval)
    return np.interp(sample_times, energy_times, energy, left=0.0, right=0.0).astype(np.float32)


def select_visual_segments(project_folder, count, min_duration, max_duration, video_duration=None, sample_interval=1.0):
    """Select speech-independent highlight windows from local visual and audio activity."""
    import cv2
    import numpy as np

    video_path = os.path.join(project_folder, "input.mp4")
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not video_duration or video_duration <= 0:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        cap.release()
        video_duration = frames / fps if fps > 0 else 0.0
    if video_duration <= 0:
        raise RuntimeError("Could not determine video duration for visual scoring")

    clip_len = min(float(max_duration), max(float(min_duration), 45.0), float(video_duration))
    print(f"[VISUAL] Sampling {video_duration:.1f}s video every {sample_interval:.1f}s...")
    times, visual = _sample_visual_activity(video_path, video_duration, sample_interval, cv2, np)
    audio = _sample_audio_activity(video_path, times, sample_interval, np)
    combined = 0.80 * visual + 0.20 * audio
    windows = _rank_windows(times, combined, clip_len, video_duration, count, np)
    if not windows:
        raise RuntimeError("Visual scoring produced no candidate windows")

    segments = []
    for index, window in enumerate(windows, start=1):
        score_100 = int(round(60 + 39 * max(0.0, min(1.0, window["score"]))))
        segments.append({
            "title": f"Visual highlight {index}",
            "start_time": window["start"],
            "end_time": window["end"],
            "hook": "Visual activity highlight",
            "reasoning": "Selected locally from motion, scene changes, image quality, and audio-energy peaks.",
            "score": score_100,
            "visual_score": round(window["score"], 4),
            "duration": window["end"] - window["start"],
        })
    print(f"[VISUAL] Selected {len(segments)} scored highlight window(s).")
    return {"segments": segments}
