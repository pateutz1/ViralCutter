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
from scripts.visual_segment_selector import _rank_windows, _robust_normalize


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


if __name__ == "__main__":
    unittest.main()
