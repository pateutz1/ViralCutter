import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.save_json import save_viral_segments


class SaveViralSegmentsTests(unittest.TestCase):
    def test_generated_segments_replace_stale_file(self):
        with tempfile.TemporaryDirectory() as project_folder:
            output = Path(project_folder) / "viral_segments.txt"
            output.write_text(json.dumps({"segments": [{"start_time": 10}]}), encoding="utf-8")
            replacement = {"segments": [{"start_time": 25, "duration": 15}]}

            save_viral_segments(replacement, project_folder=project_folder)

            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), replacement)


if __name__ == "__main__":
    unittest.main()
