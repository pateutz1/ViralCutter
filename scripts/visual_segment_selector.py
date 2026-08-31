import math
import os
import re
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
    scene_changes=None,
    scene_boundaries=None,
):
    """Rank fixed-length windows and return scene-aligned, non-overlapping selections."""
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

    boundaries = np.asarray([], dtype=np.float32)
    if scene_boundaries is not None:
        candidate_boundaries = np.asarray(scene_boundaries, dtype=np.float32)
        boundaries = candidate_boundaries[
            np.isfinite(candidate_boundaries)
            & (candidate_boundaries >= 0.0)
            & (candidate_boundaries <= float(video_duration))
        ]
        starts.extend(float(value) for value in boundaries if first_start <= value <= last_start)
    elif scene_changes is not None:
        candidate_scenes = np.asarray(scene_changes, dtype=np.float32)
        if candidate_scenes.size == times.size:
            positive = candidate_scenes[candidate_scenes > 0.0]
            if positive.size:
                boundary_threshold = max(0.55, float(np.percentile(positive, 75)))
                boundaries = times[candidate_scenes >= boundary_threshold]
                starts.extend(float(value) for value in boundaries if first_start <= value <= last_start)

    event_threshold = max(
        float(np.percentile(scores, 75)),
        float(np.median(scores) + 0.5 * np.std(scores)),
    )
    pre_roll = min(3.0, max(1.0, float(clip_len) * 0.20))
    starts.extend(
        max(first_start, min(last_start, float(event_time) - pre_roll))
        for event_time in times[scores > event_threshold]
    )

    following_boundary_guard = min(5.0, max(1.0, float(clip_len) / 3.0))
    preceding_boundary_guard = min(3.0, max(1.0, float(clip_len) * 0.20))
    aligned_starts = []
    for proposed in starts:
        start = max(first_start, min(last_start, float(proposed)))
        if boundaries.size:
            following = boundaries[
                (boundaries >= start) & (boundaries - start <= following_boundary_guard)
            ]
            preceding = boundaries[
                (boundaries < start) & (start - boundaries <= preceding_boundary_guard)
            ]
            if following.size:
                start = float(following[0])
            elif preceding.size:
                start = float(preceding[-1])
        aligned_starts.append(round(max(first_start, min(last_start, start)), 3))
    starts = sorted(set(aligned_starts))

    text_array = None
    allowed_text_ratio = max(0.0, min(1.0, float(max_text_frame_percent) / 100.0))
    if text_risks is not None:
        candidate_text = np.asarray(text_risks, dtype=np.float32)
        if candidate_text.size == times.size:
            text_array = candidate_text

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
        peak_offset = int(np.argmax(window)) / max(1, window.size - 1)
        if peak_offset < 0.10:
            activity_score *= 0.82
        elif 0.15 <= peak_offset <= 0.85:
            activity_score *= 1.04
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


def _detect_scene_boundaries(video_path, np):
    """Detect precise hard cuts without static compilation sidebars masking them."""
    command = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", video_path,
        "-vf", (
            "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=180:320,"
            "select='gt(scene,0.22)',showinfo"
        ),
        "-an", "-f", "null", "-",
    ]
    result = subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        return np.asarray([], dtype=np.float32)
    stderr = result.stderr.decode("utf-8", errors="replace")
    values = [float(value) for value in re.findall(r"pts_time:([0-9]+(?:\.[0-9]+)?)", stderr)]
    if not values:
        return np.asarray([], dtype=np.float32)
    return np.asarray(sorted(set(values)), dtype=np.float32)


def _build_text_safe_montages(
    sample_times,
    activity_scores,
    text_risks,
    clip_len,
    count,
    video_duration,
    np,
    min_range_duration=3.0,
    guard_seconds=0.5,
):
    """Build exact-duration montages from clean, non-overlapping source ranges."""
    times = np.asarray(sample_times, dtype=np.float32)
    activity = np.asarray(activity_scores, dtype=np.float32)
    risks = np.asarray(text_risks, dtype=np.float32)
    if times.size < 2 or activity.size != times.size or risks.size != times.size:
        return []

    sample_interval = float(np.median(np.diff(times)))
    clean = risks < TEXT_RISK_THRESHOLD
    runs = []
    run_start = None
    for index, is_clean in enumerate(np.append(clean, False)):
        if is_clean and run_start is None:
            run_start = index
        elif not is_clean and run_start is not None:
            run_end = index
            start = float(times[run_start])
            end = min(float(video_duration), float(times[run_end - 1]) + sample_interval)
            if run_start > 0:
                start += float(guard_seconds)
            if run_end < times.size:
                end -= float(guard_seconds)
            duration = max(0.0, end - start)
            if duration >= float(min_range_duration):
                score = float(activity[run_start:run_end].mean())
                runs.append({"start": start, "duration": duration, "score": score})
            run_start = None

    required = float(clip_len) * max(1, int(count or 1))
    if sum(item["duration"] for item in runs) + 1e-6 < required:
        return []

    ranked = sorted(
        runs,
        key=lambda item: (
            item["score"] + 0.15 * min(1.0, item["duration"] / clip_len),
            item["duration"],
        ),
        reverse=True,
    )
    chosen = []
    remaining = required
    for item in ranked:
        if remaining <= 1e-6:
            break
        take = min(item["duration"], remaining)
        chosen.append({"start": item["start"], "duration": take})
        remaining -= take

    if remaining > 1e-3:
        return []

    if chosen and chosen[-1]["duration"] < float(min_range_duration):
        deficit = float(min_range_duration) - chosen[-1]["duration"]
        for previous in reversed(chosen[:-1]):
            reducible = max(0.0, previous["duration"] - float(min_range_duration))
            moved = min(deficit, reducible)
            previous["duration"] -= moved
            chosen[-1]["duration"] += moved
            deficit -= moved
            if deficit <= 1e-6:
                break
        if deficit > 1e-6:
            return []

    chosen.sort(key=lambda item: item["start"])
    montages = []
    current = []
    current_duration = 0.0
    for item in chosen:
        source_start = item["start"]
        source_remaining = item["duration"]
        while source_remaining > 1e-6:
            room = float(clip_len) - current_duration
            take = min(source_remaining, room)
            current.append({"start_time": source_start, "duration": take})
            current_duration += take
            source_start += take
            source_remaining -= take
            if current_duration >= float(clip_len) - 1e-6:
                montages.append(current)
                current = []
                current_duration = 0.0

    return montages if len(montages) == max(1, int(count or 1)) else []

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
        # Compilation sources often place a vertical phone clip between large,
        # static sidebars. Analyze the target 9:16 content so those bars cannot
        # hide a real cut between two source scenes.
        activity_height, activity_width = activity_gray.shape
        content_width = min(activity_width, max(1, int(round(activity_height * 9.0 / 16.0))))
        content_left = max(0, (activity_width - content_width) // 2)
        content_gray = activity_gray[:, content_left:content_left + content_width]
        hist = cv2.calcHist([content_gray], [0], None, [32], [0, 256])
        cv2.normalize(hist, hist, alpha=1.0, norm_type=cv2.NORM_L1)

        motion = 0.0 if previous_gray is None else float(cv2.absdiff(content_gray, previous_gray).mean())
        scene = 0.0 if previous_hist is None else float(
            cv2.compareHist(previous_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
        )
        focus = math.log1p(float(cv2.Laplacian(content_gray, cv2.CV_64F).var()))
        brightness = float(content_gray.mean())
        exposure = max(0.0, 1.0 - abs(brightness - 127.5) / 127.5)

        times.append(frame_index * float(sample_interval))
        motions.append(motion)
        scene_changes.append(scene)
        sharpness.append(focus)
        exposure_quality.append(exposure)
        text_risks.append(_text_frame_risk(gray, cv2, np) if text_safe else 0.0)
        previous_gray = content_gray
        previous_hist = hist

    normalized_scenes = _robust_normalize(scene_changes, np)
    visual = (
        0.45 * _robust_normalize(motions, np)
        + 0.25 * normalized_scenes
        + 0.20 * _robust_normalize(sharpness, np)
        + 0.10 * np.asarray(exposure_quality, dtype=np.float32)
    )
    return (
        np.asarray(times, dtype=np.float32),
        visual,
        np.asarray(text_risks, dtype=np.float32),
        normalized_scenes,
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
    sample_interval=0.5,
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
    times, visual, text_risks, scene_changes = _sample_visual_activity(
        video_path,
        video_duration,
        sample_interval,
        cv2,
        np,
        text_safe=text_safe,
    )
    audio = _sample_audio_activity(video_path, times, sample_interval, np)
    combined = 0.80 * visual + 0.20 * audio
    precise_boundaries = _detect_scene_boundaries(video_path, np)
    if precise_boundaries.size:
        print(f"[VISUAL] Detected {precise_boundaries.size} precise scene boundaries.")
    windows = _rank_windows(
        times,
        combined,
        clip_len,
        video_duration,
        count,
        np,
        text_risks=text_risks if text_safe else None,
        max_text_frame_percent=max_text_frame_percent,
        scene_changes=scene_changes,
        scene_boundaries=precise_boundaries,
    )
    if not windows:
        raise RuntimeError("Visual scoring produced no candidate windows")

    if text_safe and not all(window.get("text_safe", False) for window in windows):
        montages = _build_text_safe_montages(
            times,
            combined,
            text_risks,
            clip_len,
            count,
            video_duration,
            np,
        )
        if not montages:
            best_percent = min(100.0 * window.get("text_frame_ratio", 1.0) for window in windows)
            raise RuntimeError(
                "Text Safe Selection could not collect enough clean footage for "
                f"{max(1, int(count or 1))} x {clip_len:.1f}s. "
                f"Best continuous window was {best_percent:.1f}% crop-risk frames. "
                "Use a shorter duration or a higher text-risk limit."
            )
        windows = [
            {
                "start": ranges[0]["start_time"],
                "end": ranges[-1]["start_time"] + ranges[-1]["duration"],
                "score": float(np.mean([
                    combined[
                        (times >= source["start_time"])
                        & (times < source["start_time"] + source["duration"])
                    ].mean()
                    for source in ranges
                ])),
                "text_safe": True,
                "text_frame_ratio": 0.0,
                "text_risk": 0.0,
                "source_ranges": ranges,
            }
            for ranges in montages
        ]
        print(
            f"[TEXT SAFE] No continuous window met the limit; built {len(windows)} "
            "clean montage(s) from multiple source ranges."
        )

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
        if window.get("source_ranges"):
            segment["duration"] = float(clip_len)
            segment["source_ranges"] = window["source_ranges"]
            segment["title"] = f"Text Safe Highlight {index}"
            segment["hook"] = "Text-safe visual montage"
            segment["reasoning"] += " Clean source ranges were joined to preserve the requested duration."
        if text_safe:
            segment.update({
                "text_safe": bool(window.get("text_safe", False)),
                "text_frame_percent": text_frame_percent,
                "text_risk": round(float(window.get("text_risk", 0.0)), 4),
            })
        segments.append(segment)
    print(f"[VISUAL] Selected {len(segments)} scored highlight window(s).")
    return {"segments": segments}
