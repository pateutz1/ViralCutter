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
sys.modules.setdefault("mediapipe", types.ModuleType("mediapipe"))

from scripts import edit_video


def _solid_bgr(color, size=(180, 320, 3)):
    frame = np.zeros(size, dtype=np.uint8)
    frame[:] = color
    return frame


def _shifted_copy(frame, dx=3, dy=2):
    moved = np.roll(frame, shift=(dy, dx), axis=(0, 1))
    return moved


class StickyFocusHelperTests(unittest.TestCase):
    def test_sticky_focus_retained_after_timeout_without_scene_cut(self):
        last = [[100, 80, 220, 240]]
        keep = edit_video.should_keep_sticky_focus(
            face_mode="auto",
            last_faces=last,
            frames_since_success=200,
            timeout_frames=90,
            scene_cut=False,
        )
        self.assertTrue(keep)

    def test_sticky_focus_cleared_after_confirmed_scene_cut(self):
        last = [[100, 80, 220, 240]]
        keep = edit_video.should_keep_sticky_focus(
            face_mode="auto",
            last_faces=last,
            frames_since_success=10,
            timeout_frames=90,
            scene_cut=True,
        )
        self.assertFalse(keep)

    def test_non_auto_still_times_out_to_fallback(self):
        last = [[100, 80, 220, 240]]
        keep = edit_video.should_keep_sticky_focus(
            face_mode="1",
            last_faces=last,
            frames_since_success=200,
            timeout_frames=90,
            scene_cut=False,
        )
        self.assertFalse(keep)

    def test_no_face_history_does_not_stick(self):
        keep = edit_video.should_keep_sticky_focus(
            face_mode="auto",
            last_faces=None,
            frames_since_success=200,
            timeout_frames=90,
            scene_cut=False,
        )
        self.assertFalse(keep)

    def test_same_scene_stays_below_cut_threshold(self):
        base = _solid_bgr((40, 80, 120))
        sig_a = edit_video.build_scene_signature(base)
        sig_b = edit_video.build_scene_signature(_shifted_copy(base))
        score = edit_video.scene_change_score(sig_a, sig_b)
        self.assertLess(score, edit_video.SCENE_CUT_SCORE_THRESHOLD)

    def test_hard_cut_needs_two_frames_to_confirm(self):
        dark = edit_video.build_scene_signature(_solid_bgr((10, 10, 10)))
        bright = edit_video.build_scene_signature(_solid_bgr((240, 220, 30)))
        score = edit_video.scene_change_score(dark, bright)
        self.assertGreaterEqual(score, edit_video.SCENE_CUT_SCORE_THRESHOLD)

        confirmed, streak = edit_video.confirm_scene_cut(score, 0)
        self.assertFalse(confirmed)
        self.assertEqual(streak, 1)

        confirmed, streak = edit_video.confirm_scene_cut(score, streak)
        self.assertTrue(confirmed)
        self.assertEqual(streak, 2)

    def test_single_flash_does_not_confirm_cut(self):
        confirmed, streak = edit_video.confirm_scene_cut(0.9, 0)
        self.assertFalse(confirmed)
        confirmed, streak = edit_video.confirm_scene_cut(0.05, streak)
        self.assertFalse(confirmed)
        self.assertEqual(streak, 0)

    def test_weak_far_detection_does_not_replace_crop(self):
        prev = [[100, 80, 220, 240]]
        jump = [[700, 80, 820, 240]]
        accept, pending, hits = edit_video.should_accept_face_update(prev, jump, None, 0)
        self.assertFalse(accept)
        self.assertEqual(hits, 1)

        accept, pending, hits = edit_video.should_accept_face_update(prev, jump, pending, hits)
        self.assertTrue(accept)
        self.assertIsNone(pending)

    def test_small_move_is_accepted_immediately(self):
        prev = [[100, 80, 220, 240]]
        near = [[110, 85, 230, 245]]
        accept, pending, hits = edit_video.should_accept_face_update(prev, near, None, 0)
        self.assertTrue(accept)
        self.assertEqual(hits, 0)


class FixedCenterUnchangedTests(unittest.TestCase):
    def test_fixed_center_still_bypasses_detectors(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            cuts = project / "cuts"
            cuts.mkdir()
            (cuts / "000_Test_original_scale.mp4").write_bytes(b"placeholder")

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
            face_modes = json.loads((project / "face_modes.json").read_text(encoding="utf-8"))
            self.assertEqual(face_modes, {"output000": "1"})


if __name__ == "__main__":
    unittest.main()
