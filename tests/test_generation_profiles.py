import sys
import unittest
from pathlib import Path


WEBUI_DIR = Path(__file__).resolve().parents[1] / "webui"
if str(WEBUI_DIR) not in sys.path:
    sys.path.insert(0, str(WEBUI_DIR))

import generation_profiles


class GenerationProfileTests(unittest.TestCase):
    def test_action_profile_configures_short_fast_auto_tracking(self):
        profile = generation_profiles.resolve_generation_profile("Human Action / Compilation")
        self.assertEqual(profile["face_mode"], "auto")
        self.assertEqual((profile["min_duration"], profile["max_duration"]), (6, 15))
        self.assertEqual(profile["face_detect_interval"], "0.12,0.25")
        self.assertLessEqual(profile["dead_zone"], 45)

    def test_non_face_profile_uses_fixed_center(self):
        profile = generation_profiles.resolve_generation_profile("Animals / Objects / Places")
        self.assertEqual(profile["face_mode"], "fixed_center")

    def test_forced_split_profile_uses_mode_2(self):
        profile = generation_profiles.resolve_generation_profile("Two Person / Forced Split")
        self.assertEqual(profile["face_mode"], "2")
        self.assertEqual(profile["face_detect_interval"], "0.17,0.30")

    def test_legacy_stable_defaults_are_migrated(self):
        migrated = generation_profiles.migrate_saved_settings({
            "face_preset": "Stable (Focus Main)",
            "face_filter_thresh": 0.60,
            "face_two_thresh": 0.80,
            "face_conf_thresh": 0.60,
            "face_dead_zone": 200,
            "face_detect_interval": "0.17,1.0",
        })
        self.assertEqual(migrated["face_dead_zone"], 70)
        self.assertEqual(migrated["face_detect_interval"], "0.17,0.35")

    def test_custom_face_values_are_preserved(self):
        migrated = generation_profiles.migrate_saved_settings({
            "face_preset": "Stable (Focus Main)",
            "face_filter_thresh": 0.51,
            "face_two_thresh": 0.71,
            "face_conf_thresh": 0.61,
            "face_dead_zone": 55,
            "face_detect_interval": "0.10,0.20",
        })
        self.assertEqual(migrated["face_dead_zone"], 55)
        self.assertEqual(migrated["face_detect_interval"], "0.10,0.20")


if __name__ == "__main__":
    unittest.main()
