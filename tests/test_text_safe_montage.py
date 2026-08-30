import sys
import types
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
scripts_package = sys.modules.setdefault("scripts", types.ModuleType("scripts"))
scripts_package.__path__ = [str(PROJECT_ROOT / "scripts")]

from scripts import cut_json, cut_segments
from scripts.visual_segment_selector import (
    TEXT_RISK_THRESHOLD,
    _build_text_safe_montages,
)


class TextSafeMontageTests(unittest.TestCase):
    def test_builds_exact_duration_from_clean_ranges(self):
        times = np.arange(0, 240, dtype=np.float32)
        activity = np.linspace(0.1, 1.0, len(times), dtype=np.float32)
        risks = np.zeros_like(times)
        risks[40:60] = 0.5
        risks[120:150] = 0.5

        montages = _build_text_safe_montages(
            times, activity, risks, 120, 1, 240, np
        )

        self.assertEqual(len(montages), 1)
        self.assertAlmostEqual(sum(item["duration"] for item in montages[0]), 120.0)
        self.assertEqual(montages[0], sorted(montages[0], key=lambda item: item["start_time"]))
        self.assertTrue(all(item["duration"] >= 3.0 for item in montages[0]))
        for source in montages[0]:
            mask = (
                (times >= source["start_time"])
                & (times < source["start_time"] + source["duration"])
            )
            self.assertTrue(np.all(risks[mask] < TEXT_RISK_THRESHOLD))

    def test_returns_empty_when_clean_footage_is_insufficient(self):
        times = np.arange(0, 60, dtype=np.float32)
        activity = np.ones_like(times)
        risks = np.full_like(times, 0.5)

        self.assertEqual(
            _build_text_safe_montages(times, activity, risks, 30, 1, 60, np),
            [],
        )

    def test_ffmpeg_command_concatenates_video_and_audio_ranges(self):
        ranges = [
            {"start_time": 10.0, "duration": 4.0},
            {"start_time": 30.0, "duration": 6.0},
        ]

        command = cut_segments._build_montage_command(
            "input.mp4", "output.mp4", ranges, "libx264", has_audio=True
        )
        filter_complex = command[command.index("-filter_complex") + 1]

        self.assertIn("trim=start=10.000000:duration=4.000000", filter_complex)
        self.assertIn("atrim=start=30.000000:duration=6.000000", filter_complex)
        self.assertIn("concat=n=2:v=1:a=1[vout][aout]", filter_complex)
        self.assertIn("[aout]", command)
        self.assertEqual(command[command.index("-t") + 1], "10.000000")

    def test_transcript_ranges_are_shifted_to_montage_timeline(self):
        data = {
            "segments": [
                {"start": 10.0, "end": 12.0, "text": "first"},
                {"start": 50.0, "end": 52.0, "text": "second"},
            ]
        }
        ranges = [
            {"start_time": 10.0, "duration": 3.0},
            {"start_time": 50.0, "duration": 3.0},
        ]

        result = cut_json.process_segment_ranges(data, ranges)

        self.assertEqual(len(result["segments"]), 2)
        self.assertAlmostEqual(result["segments"][0]["start"], 0.0)
        self.assertAlmostEqual(result["segments"][1]["start"], 3.0)
        self.assertAlmostEqual(result["segments"][1]["end"], 5.0)


if __name__ == "__main__":
    unittest.main()
