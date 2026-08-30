import math
import os
import subprocess

TEXT_RISK_THRESHOLD = 0.18


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


def _text_frame_risk(gray, cv2, np):
    """Estimate whether text-like regions would be clipped by a centered 9:16 crop."""
    height, width = gray.shape
    gradient = cv2.convertScaleAbs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))
    _, edges = cv2.threshold(gradient, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    grouped = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3)),
    )
    contours, _ = cv2.findContours(grouped, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    safe_width = min(float(width), float(height) * 9.0 / 16.0)
    safe_left = (float(width) - safe_width) / 2.0
    safe_right = safe_left + safe_width
    regions = []
    for contour in contours:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        aspect = float(box_width) / max(1.0, float(box_height))
        if (
            box_width < width * 0.05
            or box_height < height * 0.015
            or box_height > height * 0.24
            or aspect < 1.2
        ):
            continue

        edge_density = float(cv2.countNonZero(edges[y:y + box_height, x:x + box_width]))
        edge_density /= max(1.0, float(box_width * box_height))
        if edge_density < 0.03 or edge_density > 0.80:
            continue

        overlap = max(0.0, min(x + box_width, safe_right) - max(x, safe_left))
        outside_fraction = 1.0 - overlap / max(1.0, float(box_width))
        size_factor = min(1.0, box_width / (width * 0.35))
        size_factor *= min(1.0, box_height / (height * 0.05))
        regions.append(size_factor * (0.25 + 0.75 * outside_fraction))

    regions.sort(reverse=True)
    return min(1.0, sum(regions[:3]) * 0.55)


def _rank_windows(
    sample_times,
    activity_scores,
    clip_len,
    video_duration,
    count,
    np,
    pad=None,
    stride=None,
    text_risks=None,
    max_text_frame_percent=15.0,
):
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

    text_array = None
    allowed_text_ratio = max(0.0, min(1.0, float(max_text_frame_percent) / 100.0))
    if text_risks is not None:
        candidate_text = np.asarray(text_risks, dtype=np.float32)
        if candidate_text.size == times.size:
            text_array = candidate_text

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
        activity_score = 0.55 * mean_score + 0.30 * peak_score + 0.15 * event_density
        candidate = {"start": start, "end": end, "score": activity_score}
        if text_array is not None:
            window_text = text_array[mask]
            text_frame_ratio = float((window_text >= TEXT_RISK_THRESHOLD).mean())
            text_risk = float(window_text.mean())
            candidate.update({
                "score": activity_score * (1.0 - 0.35 * text_risk),
                "activity_score": activity_score,
                "text_risk": text_risk,
                "text_frame_ratio": text_frame_ratio,
                "text_safe": text_frame_ratio <= allowed_text_ratio,
            })
        candidates.append(candidate)

    if text_array is None:
        candidates.sort(key=lambda item: item["score"], reverse=True)
    else:
        candidates.sort(
            key=lambda item: (
                0 if item["text_safe"] else 1,
                -item["score"] if item["text_safe"] else item["text_frame_ratio"],
                item["text_risk"] if not item["text_safe"] else -item["activity_score"],
            )
        )

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


def _sample_visual_activity(video_path, video_duration, sample_interval, cv2, np, text_safe=False):
    times = []
    motions = []
    scene_changes = []
    sharpness = []
    exposure_quality = []
    text_risks = []
    previous_gray = None
    previous_hist = None

    width, height = (320, 180) if text_safe else (160, 90)
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
        activity_gray = cv2.resize(gray, (160, 90), interpolation=cv2.INTER_AREA) if text_safe else gray
        hist = cv2.calcHist([activity_gray], [0], None, [32], [0, 256])
        cv2.normalize(hist, hist, alpha=1.0, norm_type=cv2.NORM_L1)

        motion = 0.0 if previous_gray is None else float(cv2.absdiff(activity_gray, previous_gray).mean())
        scene = 0.0 if previous_hist is None else float(
            cv2.compareHist(previous_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
        )
        focus = math.log1p(float(cv2.Laplacian(activity_gray, cv2.CV_64F).var()))
        brightness = float(activity_gray.mean())
        exposure = max(0.0, 1.0 - abs(brightness - 127.5) / 127.5)

        times.append(frame_index * float(sample_interval))
        motions.append(motion)
        scene_changes.append(scene)
        sharpness.append(focus)
        exposure_quality.append(exposure)
        text_risks.append(_text_frame_risk(gray, cv2, np) if text_safe else 0.0)
        previous_gray = activity_gray
        previous_hist = hist

    visual = (
        0.45 * _robust_normalize(motions, np)
        + 0.25 * _robust_normalize(scene_changes, np)
        + 0.20 * _robust_normalize(sharpness, np)
        + 0.10 * np.asarray(exposure_quality, dtype=np.float32)
    )
    return (
        np.asarray(times, dtype=np.float32),
        visual,
        np.asarray(text_risks, dtype=np.float32),
    )


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


def select_visual_segments(
    project_folder,
    count,
    min_duration,
    max_duration,
    video_duration=None,
    sample_interval=1.0,
    text_safe=False,
    max_text_frame_percent=15.0,
):
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
    times, visual, text_risks = _sample_visual_activity(
        video_path,
        video_duration,
        sample_interval,
        cv2,
        np,
        text_safe=text_safe,
    )
    audio = _sample_audio_activity(video_path, times, sample_interval, np)
    combined = 0.80 * visual + 0.20 * audio
    windows = _rank_windows(
        times,
        combined,
        clip_len,
        video_duration,
        count,
        np,
        text_risks=text_risks if text_safe else None,
        max_text_frame_percent=max_text_frame_percent,
    )
    if not windows:
        raise RuntimeError("Visual scoring produced no candidate windows")

    segments = []
    for index, window in enumerate(windows, start=1):
        score_100 = int(round(60 + 39 * max(0.0, min(1.0, window["score"]))))
        reasoning = "Selected locally from motion, scene changes, image quality, and audio-energy peaks."
        if text_safe:
            text_frame_percent = round(100.0 * window.get("text_frame_ratio", 0.0), 1)
            reasoning += f" Text-safe analysis estimated {text_frame_percent}% crop-risk frames."
            print(
                f"[TEXT SAFE] Highlight {index}: {text_frame_percent}% crop-risk frames "
                f"(limit {float(max_text_frame_percent):.1f}%)."
            )
        segment = {
            "title": f"Visual highlight {index}",
            "start_time": window["start"],
            "end_time": window["end"],
            "hook": "Visual activity highlight",
            "reasoning": reasoning,
            "score": score_100,
            "visual_score": round(window["score"], 4),
            "duration": window["end"] - window["start"],
        }
        if text_safe:
            segment.update({
                "text_safe": bool(window.get("text_safe", False)),
                "text_frame_percent": text_frame_percent,
                "text_risk": round(float(window.get("text_risk", 0.0)), 4),
            })
        segments.append(segment)
    print(f"[VISUAL] Selected {len(segments)} scored highlight window(s).")
    return {"segments": segments}
