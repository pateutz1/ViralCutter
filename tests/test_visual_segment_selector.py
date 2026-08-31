import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
scripts_package = types.ModuleType("scripts")
scripts_package.__path__ = [str(PROJECT_ROOT / "scripts")]
sys.modules["scripts"] = scripts_package

from scripts import create_viral_segments
from scripts.visual_segment_selector import _rank_windows, _robust_normalize, _text_frame_risk


class VisualSegmentSelectorTests(unittest.TestCase):
    def test_robust_normalize_is_bounded(self):
        result = _robust_normalize([0, 1, 2, 100], np)
        self.assertEqual(result.shape, (4,))
        self.assertGreaterEqual(float(result.min()), 0.0)
        self.assertLessEqual(float(result.max()), 1.0)

    def test_rank_windows_selects_activity_cluster(self):
        times = np.arange(0, 180, dtype=np.float32)
        scores = np.zeros_like(times)
        scores[(times >= 70) & (times < 100)] = 1.0

        result = _rank_windows(times, scores, 30, 180, 1, np, pad=0, stride=5)

        self.assertEqual(len(result), 1)
        self.assertGreaterEqual(result[0]["start"], 65.0)
        self.assertLessEqual(result[0]["start"], 75.0)
        self.assertAlmostEqual(result[0]["end"] - result[0]["start"], 30.0)

    def test_rank_windows_returns_non_overlapping_results(self):
        times = np.arange(0, 200, dtype=np.float32)
        scores = np.zeros_like(times)
        scores[(times >= 25) & (times < 50)] = 1.0
        scores[(times >= 140) & (times < 165)] = 0.9

        result = _rank_windows(times, scores, 25, 200, 2, np, pad=0, stride=5)

        self.assertEqual(len(result), 2)
        overlap = min(result[0]["end"], result[1]["end"]) - max(result[0]["start"], result[1]["start"])
        self.assertLessEqual(overlap, 5.0)

    def test_rank_windows_drops_short_previous_scene_tail(self):
        times = np.arange(0, 40, 0.5, dtype=np.float32)
        scores = np.full_like(times, 0.1)
        scores[(times >= 13) & (times < 22)] = 1.0
        scenes = np.zeros_like(times)
        scenes[times == 10.5] = 1.0

        result = _rank_windows(
            times, scores, 15, 40, 1, np, pad=0, stride=5, scene_changes=scenes
        )

        self.assertEqual(result[0]["start"], 10.5)
        self.assertAlmostEqual(result[0]["end"] - result[0]["start"], 15.0)

    def test_rank_windows_drops_five_second_previous_scene_tail(self):
        times = np.arange(0, 50, 0.5, dtype=np.float32)
        scores = np.full_like(times, 0.1)
        scores[(times >= 20) & (times < 32)] = 1.0
        scenes = np.zeros_like(times)
        scenes[times == 20] = 1.0

        result = _rank_windows(
            times, scores, 15, 50, 1, np, pad=0, stride=5, scene_changes=scenes
        )

        self.assertEqual(result[0]["start"], 20.0)

    def test_precise_boundaries_override_missed_sampled_scene(self):
        times = np.arange(0, 50, 0.5, dtype=np.float32)
        scores = np.full_like(times, 0.1)
        scores[(times >= 22) & (times < 32)] = 1.0
        sampled_scenes = np.zeros_like(times)

        result = _rank_windows(
            times,
            scores,
            15,
            50,
            1,
            np,
            pad=0,
            stride=5,
            scene_changes=sampled_scenes,
            scene_boundaries=[20.125],
        )

        self.assertEqual(result[0]["start"], 20.125)

    def test_rank_windows_keeps_preroll_before_activity_peak(self):
        times = np.arange(0, 40, 0.5, dtype=np.float32)
        scores = np.full_like(times, 0.1)
        scores[times == 18] = 1.0

        result = _rank_windows(times, scores, 15, 40, 1, np, pad=0, stride=5)

        self.assertLessEqual(result[0]["start"], 15.0)
        self.assertGreaterEqual(18.0 - result[0]["start"], 3.0)

    @mock.patch("scripts.visual_segment_selector.select_visual_segments")
    def test_low_speech_fallback_uses_visual_selector(self, select_visual_segments):
        expected = {"segments": [{"start_time": 10.0, "duration": 90.0}]}
        select_visual_segments.return_value = expected

        result = create_viral_segments._fallback_visual_segments("project", 1, 90, 90, 120)

        self.assertEqual(result, expected)
        select_visual_segments.assert_called_once_with(
            "project", 1, 90, 90, video_duration=120
        )

    @mock.patch("scripts.visual_segment_selector.select_visual_segments", side_effect=RuntimeError("decode failed"))
    def test_visual_failure_keeps_timeline_safety_net(self, _select_visual_segments):
        result = create_viral_segments._fallback_visual_segments("project", 1, 90, 90, 120)

        self.assertEqual(len(result["segments"]), 1)
        self.assertAlmostEqual(result["segments"][0]["duration"], 90.0)


    def test_text_risk_flags_wide_and_corner_text_outside_crop(self):
        import cv2

        blank = np.zeros((180, 320), dtype=np.uint8)
        wide = blank.copy()
        corner = blank.copy()
        centered = blank.copy()
        cv2.putText(wide, "I HOPE WE GET A STUPID CAT", (2, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 255, 2, cv2.LINE_AA)
        cv2.putText(corner, "@OWNER", (235, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 255, 1, cv2.LINE_AA)
        cv2.putText(centered, "CAT", (135, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 255, 2, cv2.LINE_AA)

        self.assertEqual(_text_frame_risk(blank, cv2, np), 0.0)
        self.assertGreater(_text_frame_risk(wide, cv2, np), 0.25)
        self.assertGreater(_text_frame_risk(corner, cv2, np), 0.18)
        self.assertLess(_text_frame_risk(centered, cv2, np), 0.18)

    def test_rank_windows_prefers_text_safe_activity_window(self):
        times = np.arange(0, 240, dtype=np.float32)
        activity = np.zeros_like(times)
        activity[(times >= 0) & (times < 60)] = 1.0
        activity[(times >= 120) & (times < 180)] = 0.7
        text_risks = np.zeros_like(times)
        text_risks[(times >= 0) & (times < 60)] = 0.5

        result = _rank_windows(
            times,
            activity,
            60,
            240,
            1,
            np,
            pad=0,
            stride=60,
            text_risks=text_risks,
            max_text_frame_percent=15,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start"], 120.0)
        self.assertTrue(result[0]["text_safe"])

    @mock.patch("scripts.create_viral_segments._fallback_visual_segments")
    @mock.patch("scripts.create_viral_segments._video_duration", return_value=240)
    def test_text_safe_mode_bypasses_transcript_ai_and_forwards_limit(self, _duration, fallback):
        fallback.return_value = {"segments": [{"start_time": 120.0, "duration": 90.0}]}

        result = create_viral_segments.create(
            1,
            True,
            "",
            90,
            90,
            project_folder="project",
            text_safe_selection=True,
            max_text_frame_percent=12,
        )

        self.assertEqual(result, fallback.return_value)
        fallback.assert_called_once_with(
            "project",
            1,
            90,
            90,
            240,
            text_safe_selection=True,
            max_text_frame_percent=12,
        )

if __name__ == "__main__":
    unittest.main()
