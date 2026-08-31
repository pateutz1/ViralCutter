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


def _structured_scene(kind, size=(180, 320, 3)):
    height, width = size[:2]
    rows, cols = np.mgrid[0:height, 0:width]
    frame = np.zeros(size, dtype=np.uint8)
    if kind == "a":
        frame[:, :, 0] = (cols // 16 * 18) % 160
        frame[:, :, 1] = (rows // 12 * 14) % 120
        frame[:, :, 2] = 35
    else:
        frame[:, :, 0] = 255 - (rows // 10 * 22) % 200
        frame[:, :, 1] = 210
        frame[:, :, 2] = (cols // 8 * 31) % 255
    return frame


def _translate(frame, dx, dy):
    return np.roll(frame, shift=(dy, dx), axis=(0, 1))


def _feed(tracker, frame):
    return tracker.update(edit_video.build_scene_signature(frame))


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

    def test_mode_1_also_keeps_sticky_focus_after_timeout(self):
        last = [[100, 80, 220, 240]]
        keep = edit_video.should_keep_sticky_focus(
            face_mode="1",
            last_faces=last,
            frames_since_success=200,
            timeout_frames=90,
            scene_cut=False,
        )
        self.assertTrue(keep)
        self.assertTrue(edit_video.uses_sticky_focus("1"))

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

    def test_mode_2_still_times_out_to_fallback(self):
        last = [[100, 80, 220, 240]]
        keep = edit_video.should_keep_sticky_focus(
            face_mode="2",
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

    def test_textured_camera_motion_does_not_confirm_cut(self):
        base = _structured_scene("a")
        tracker = edit_video.SceneCutTracker()
        cuts = 0
        for step in range(8):
            if _feed(tracker, _translate(base, dx=step * 3, dy=step * 2)):
                cuts += 1
        self.assertEqual(cuts, 0)

    def test_one_frame_flash_does_not_confirm_cut(self):
        scene = _structured_scene("a")
        flash = np.full_like(scene, 255)
        tracker = edit_video.SceneCutTracker()
        self.assertFalse(_feed(tracker, scene))
        self.assertFalse(_feed(tracker, scene))
        self.assertFalse(_feed(tracker, flash))
        self.assertFalse(_feed(tracker, scene))

    def test_hard_cut_to_stable_new_scene_confirms_once(self):
        scene_a = _structured_scene("a")
        scene_b = _structured_scene("b")
        tracker = edit_video.SceneCutTracker()
        self.assertFalse(_feed(tracker, scene_a))
        self.assertFalse(_feed(tracker, scene_a))
        self.assertFalse(_feed(tracker, scene_b))
        self.assertTrue(_feed(tracker, scene_b))
        extra_cuts = sum(1 for _ in range(6) if _feed(tracker, scene_b))
        self.assertEqual(extra_cuts, 0)

    def test_lookahead_respects_confidence_threshold(self):
        faces = [{"bbox": [10, 10, 80, 90], "det_score": 0.60}]
        rejected = edit_video.prepare_insightface_faces(faces, 0.75, 0.35)
        accepted = edit_video.prepare_insightface_faces(
            [{"bbox": [10, 10, 80, 90], "det_score": 0.60}],
            0.40,
            0.35,
        )
        self.assertEqual(rejected, [])
        self.assertEqual(len(accepted), 1)

    def test_tiny_false_face_is_rejected_by_min_height(self):
        # 38px tall on 1080p is the cooler/rock false lock from highlight 1.
        faces = [{"bbox": [823, 353, 861, 393], "det_score": 0.62}]
        kept = edit_video.prepare_insightface_faces(faces, 0.40, 0.35, frame_height=1080)
        self.assertEqual(kept, [])

    def test_170px_jump_requires_confirmation_even_with_stable_dead_zone(self):
        prev = [[100, 80, 220, 240]]
        jumped = [[270, 80, 390, 240]]
        self.assertGreater(edit_video.max_bbox_center_distance(prev, jumped), 169)
        self.assertLess(edit_video.STICKY_JUMP_PX, 200)

        accept, pending, hits = edit_video.should_accept_face_update(
            prev, jumped, None, 0, jump_px=edit_video.STICKY_JUMP_PX,
        )
        self.assertFalse(accept)
        accept, pending, hits = edit_video.should_accept_face_update(
            prev, jumped, pending, hits, jump_px=edit_video.STICKY_JUMP_PX,
        )
        self.assertTrue(accept)

    def test_small_move_is_accepted_immediately(self):
        prev = [[100, 80, 220, 240]]
        near = [[110, 85, 230, 245]]
        accept, pending, hits = edit_video.should_accept_face_update(prev, near, None, 0)
        self.assertTrue(accept)
        self.assertEqual(hits, 0)

    def test_new_face_after_cleared_crop_is_accepted_immediately(self):
        accept, pending, hits = edit_video.should_accept_face_update(
            None, [[400, 80, 520, 240]], None, 0,
        )
        self.assertTrue(accept)


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
