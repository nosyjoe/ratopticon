import unittest

from ratopticon import camera_ctrl


class TestCameraCtrl(unittest.TestCase):
    def test_augment_setting_with_hint_does_not_mutate_source(self):
        source_key = "bitrate"
        source_before = camera_ctrl.user_modifiable_video_settings_info[source_key].copy()

        augmented = camera_ctrl.augment_setting_with_hint(source_key, "123")

        self.assertEqual(source_before, camera_ctrl.user_modifiable_video_settings_info[source_key])
        self.assertIn("value", augmented)
        self.assertEqual("123", augmented["value"])


if __name__ == "__main__":
    unittest.main()
