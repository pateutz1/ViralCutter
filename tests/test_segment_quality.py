import sys
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
scripts_package = sys.modules.setdefault("scripts", types.ModuleType("scripts"))
scripts_package.__path__ = [str(PROJECT_ROOT / "scripts")]

from scripts.create_viral_segments import (
    dedupe_aligned_segments,
    dedupe_raw_candidates,
    process_segments,
)


class SegmentQualityTests(unittest.TestCase):
    def test_raw_dedupe_requires_reference_and_text_agreement(self):
        candidates = [
            {
                "title": "Funny cat",
                "start_text": "the cat opens the door",
                "end_text": "everyone starts laughing",
                "start_time_ref": "(100s)",
                "score": 95,
            },
            {
                "title": "Funny cat duplicate",
                "start_text": "the cat opens the door",
                "end_text": "everyone starts laughing",
                "start_time_ref": "(106s)",
                "score": 80,
            },
            {
                "title": "Funny cat",
                "start_text": "a different dog runs outside",
                "end_text": "the owner closes the gate",
                "start_time_ref": "(105s)",
                "score": 85,
            },
            {
                "title": "Funny cat",
                "start_text": "the cat opens the door",
                "end_text": "everyone starts laughing",
                "start_time_ref": "(300s)",
                "score": 75,
            },
        ]

        result = dedupe_raw_candidates(candidates)

        self.assertEqual([item["score"] for item in result], [95, 85, 75])

    def test_aligned_dedupe_keeps_highest_score(self):
        segments = [
            {"title": "best", "start_time": 0.0, "end_time": 60.0, "score": 95},
            {"title": "duplicate", "start_time": 55.0, "end_time": 115.0, "score": 80},
            {"title": "separate", "start_time": 130.0, "end_time": 190.0, "score": 90},
        ]

        result = dedupe_aligned_segments(segments, min_separation=10.0)

        self.assertEqual([item["title"] for item in result], ["best", "separate"])

    def test_missing_end_text_does_not_create_fake_duration(self):
        transcript = [
            {"start": 0.0, "end": 10.0, "text": "the cat opens the door"},
            {"start": 10.0, "end": 20.0, "text": "everyone watches"},
            {"start": 20.0, "end": 30.0, "text": "the dog runs away"},
        ]
        candidate = {
            "title": "missing end",
            "start_text": "the cat opens the door",
            "end_text": "words that are not in transcript",
            "start_time_ref": "(0s)",
            "score": 90,
        }

        result = process_segments([candidate], transcript, 20, 30, output_count=1)

        self.assertEqual(result, {"segments": []})

    def test_reliable_candidate_wins_over_low_confidence_candidate(self):
        transcript = [
            {"start": 0.0, "end": 10.0, "text": "the cat opens the door"},
            {"start": 10.0, "end": 20.0, "text": "everyone watches"},
            {"start": 20.0, "end": 30.0, "text": "everyone starts laughing"},
            {"start": 40.0, "end": 50.0, "text": "a dog enters the room"},
            {"start": 50.0, "end": 60.0, "text": "the owner looks surprised"},
        ]
        candidates = [
            {
                "title": "reliable",
                "start_text": "the cat opens the door",
                "end_text": "everyone starts laughing",
                "start_time_ref": "(0s)",
                "score": 95,
            },
            {
                "title": "low confidence",
                "start_text": "a dog enters the room",
                "end_text": "missing ending words",
                "start_time_ref": "(40s)",
                "score": 90,
            },
        ]

        result = process_segments(candidates, transcript, 10, 30, output_count=2)

        self.assertEqual(len(result["segments"]), 1)
        self.assertEqual(result["segments"][0]["title"], "reliable")
        self.assertEqual(result["segments"][0]["alignment_confidence"], "high")


if __name__ == "__main__":
    unittest.main()
