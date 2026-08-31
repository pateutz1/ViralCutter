import os
import sys
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
scripts_package = sys.modules.setdefault("scripts", types.ModuleType("scripts"))
scripts_package.__path__ = [str(PROJECT_ROOT / "scripts")]

from scripts.cut_segments import _parse_seconds
from scripts.download_video import SUBTITLE_LANGS, _format_vtt_lines


class BatchABugfixTests(unittest.TestCase):
    def test_long_video_timestamps_remain_seconds(self):
        self.assertEqual(_parse_seconds(1200, True), 1200.0)
        self.assertEqual(_parse_seconds("1200", True), 1200.0)
        self.assertEqual(_parse_seconds("00:20:00", True), 1200.0)
        self.assertEqual(_parse_seconds("20:00", True), 1200.0)

    def test_legacy_large_millisecond_values_are_supported(self):
        self.assertEqual(_parse_seconds(120000, True), 120.0)
        self.assertEqual(_parse_seconds("120000", True), 120.0)

    def test_invalid_timestamps_are_rejected(self):
        with self.assertRaises(ValueError):
            _parse_seconds(-1, True)
        with self.assertRaises(ValueError):
            _parse_seconds("not-a-time", True)

    def test_spanish_subtitle_language_code_is_es(self):
        self.assertIn("es.*", SUBTITLE_LANGS)
        self.assertNotIn("sp.*", SUBTITLE_LANGS)

    def test_vtt_text_before_timestamp_is_ignored(self):
        lines = [
            "WEBVTT\n",
            "orphan text\n",
            "00:01.000 --> 00:02.500 align:start position:0%\n",
            "<c>Hello cats</c>\n",
            "\n",
            "another orphan\n",
        ]

        result = _format_vtt_lines(lines)

        self.assertEqual(
            result,
            ["1\n", "00:00:01,000 --> 00:00:02,500\n", "Hello cats\n\n"],
        )


if __name__ == "__main__":
    unittest.main()
