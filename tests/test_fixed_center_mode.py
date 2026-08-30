import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
scripts_package = types.ModuleType("scripts")
scripts_package.__path__ = [str(PROJECT_ROOT / "scripts")]
sys.modules["scripts"] = scripts_package
sys.modules.setdefault("mediapipe", types.ModuleType("mediapipe"))

from scripts import edit_video


class FixedCenterModeTests(unittest.TestCase):
    def test_fixed_center_bypasses_detectors_and_forces_zoom(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            cuts = project / "cuts"
            cuts.mkdir()
            input_file = cuts / "000_Test_original_scale.mp4"
            input_file.write_bytes(b"placeholder")

            def fake_render(_input, _output, index, _project, final_folder, no_face_mode):
                self.assertEqual(no_face_mode, "zoom")
                Path(final_folder, f"final-output{index:03d}_processed.mp4").write_bytes(b"video")

            with mock.patch.object(edit_video, "INSIGHTFACE_AVAILABLE", True), \
                 mock.patch.object(edit_video, "init_insightface") as init_insightface, \
                 mock.patch.object(edit_video, "generate_short_fallback", side_effect=fake_render) as fallback:
                edit_video.edit(
                    project_folder=str(project),
                    face_model="insightface",
                    face_mode="fixed_center",
                    no_face_mode="padding",
                )

            init_insightface.assert_not_called()
            fallback.assert_called_once()
            self.assertTrue((project / "final" / "000_Test.mp4").exists())
            face_modes = json.loads((project / "face_modes.json").read_text(encoding="utf-8"))
            self.assertEqual(face_modes, {"output000": "1"})


if __name__ == "__main__":
    unittest.main()