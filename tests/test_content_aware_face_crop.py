import unittest
import sys
import types

import numpy as np

sys.modules.setdefault("mediapipe", types.ModuleType("mediapipe"))

from scripts.content_bounds import detect_embedded_content_bounds
from scripts.face_detection_insightface import crop_and_resize_insightface
from scripts.one_face import crop_center_zoom
from scripts.two_face import crop_and_resize_two_faces


class ContentBoundsTests(unittest.TestCase):
    @staticmethod
    def embedded_frame():
        rng = np.random.default_rng(42)
        frame = np.full((180, 320, 3), (120, 130, 105), dtype=np.uint8)
        frame[:, 68:252] = rng.integers(10, 245, size=(180, 184, 3), dtype=np.uint8)
        return frame

    def test_detects_uniform_side_pillars(self):
        bounds = detect_embedded_content_bounds(self.embedded_frame())
        self.assertIsNotNone(bounds)
        self.assertLessEqual(abs(bounds[0] - 69), 2)
        self.assertLessEqual(abs(bounds[1] - 251), 2)

    def test_native_textured_frame_is_not_restricted(self):
        rng = np.random.default_rng(7)
        frame = rng.integers(0, 256, size=(180, 320, 3), dtype=np.uint8)
        self.assertIsNone(detect_embedded_content_bounds(frame))

    def test_edge_face_crop_stays_inside_content(self):
        frame = self.embedded_frame()
        bounds = detect_embedded_content_bounds(frame)
        result = crop_and_resize_insightface(
            frame,
            np.array([235, 55, 255, 90]),
            target_width=108,
            target_height=192,
            content_bounds=bounds,
        )
        pillar = np.array([120, 130, 105], dtype=np.uint8)
        self.assertLess(np.mean(np.all(result == pillar, axis=2)), 0.001)

    def test_no_face_zoom_stays_inside_content(self):
        frame = self.embedded_frame()
        bounds = detect_embedded_content_bounds(frame)
        result = crop_center_zoom(frame, content_bounds=bounds)
        pillar = np.array([120, 130, 105], dtype=np.uint8)
        self.assertLess(np.mean(np.all(result == pillar, axis=2)), 0.001)

    def test_two_face_panes_stay_inside_content(self):
        frame = self.embedded_frame()
        bounds = detect_embedded_content_bounds(frame)
        result = crop_and_resize_two_faces(
            frame,
            [(70, 50, 20, 30), (232, 50, 20, 30)],
            content_bounds=bounds,
        )
        self.assertEqual(result.shape, (1920, 1080, 3))
        pillar = np.array([120, 130, 105], dtype=np.uint8)
        self.assertLess(np.mean(np.all(result == pillar, axis=2)), 0.001)


if __name__ == "__main__":
    unittest.main()
