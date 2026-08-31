import cv2
import numpy as np


CONTENT_SAMPLE_WIDTH = 320
MIN_SIDE_BAR_FRACTION = 0.03
MAX_CONTENT_FRACTION = 0.94


def normalize_content_bounds(frame_width, content_bounds=None):
    """Return a safe [left, right) horizontal content interval."""
    if not content_bounds:
        return 0, int(frame_width)
    left, right = (int(round(value)) for value in content_bounds[:2])
    left = max(0, min(left, int(frame_width) - 1))
    right = max(left + 1, min(right, int(frame_width)))
    return left, right


def detect_embedded_content_bounds(frame, sample_width=CONTENT_SAMPLE_WIDTH):
    """Detect symmetric or uniform side pillars around embedded video content.

    Returns ``(left, right)`` in source pixels, or ``None`` when the frame looks
    like native full-width content. The detector deliberately requires long,
    visually uniform edge runs so ordinary sky, walls, and camera motion are
    not treated as letterboxing.
    """
    if frame is None or getattr(frame, "size", 0) == 0:
        return None

    height, width = frame.shape[:2]
    if width < 32 or height < 32:
        return None

    scaled_width = min(int(sample_width), int(width))
    scaled_height = max(64, int(round(height * scaled_width / width)))
    small = cv2.resize(frame, (scaled_width, scaled_height), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).astype(np.float32)
    vertical = lab[int(scaled_height * 0.18):int(scaled_height * 0.92)]
    reference_columns = max(2, scaled_width // 100)

    def scan_from_edge(reverse=False):
        pixels = vertical[:, ::-1] if reverse else vertical
        reference = np.median(pixels[:, :reference_columns], axis=(0, 1))
        distance = np.linalg.norm(pixels - reference, axis=2)
        column_distance = np.mean(distance, axis=0)
        column_match = np.mean(distance < 14.0, axis=0)

        limit = int(scaled_width * 0.45)
        for index in range(2, limit):
            window = slice(index - 2, index + 1)
            if np.mean(column_distance[window]) > 18.0 and np.mean(column_match[window]) < 0.70:
                bar_width = index - 2
                if bar_width <= 0:
                    return 0, 0.0, 0.0
                return (
                    bar_width,
                    float(np.mean(column_distance[:bar_width])),
                    float(np.mean(column_match[:bar_width])),
                )
        return 0, 0.0, 0.0

    left_bar, left_distance, left_match = scan_from_edge(False)
    right_bar, right_distance, right_match = scan_from_edge(True)
    minimum_bar = max(2, int(round(scaled_width * MIN_SIDE_BAR_FRACTION)))
    content_width = scaled_width - left_bar - right_bar

    if left_bar < minimum_bar or right_bar < minimum_bar:
        return None
    if content_width <= 0 or content_width > scaled_width * MAX_CONTENT_FRACTION:
        return None
    if left_match < 0.94 or right_match < 0.94:
        return None
    if left_distance > 6.0 or right_distance > 6.0:
        return None

    # Keep the crop just inside the detected seam so resampling cannot pull a
    # one-pixel strip of the pillar into the final portrait video.
    inset = 2
    left = int(round((left_bar + inset) * width / scaled_width))
    right = int(round((scaled_width - right_bar - inset) * width / scaled_width))
    if right - left < max(8, int(width * 0.20)):
        return None
    return left, right


def bounds_are_close(first, second, tolerance=24):
    if not first or not second:
        return False
    return abs(first[0] - second[0]) <= tolerance and abs(first[1] - second[1]) <= tolerance
