import os
from unittest.mock import patch
import unittest

from dnafx_preset.config import DEFAULT_OUT_ENDPOINT, DEFAULT_PRODUCT_ID, DEFAULT_VENDOR_ID, DeviceConfig


class DeviceConfigTests(unittest.TestCase):
    def test_uses_dnafx_git_defaults_when_usb_values_are_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = DeviceConfig.from_sources()

        self.assertEqual(config.vendor_id, DEFAULT_VENDOR_ID)
        self.assertEqual(config.product_id, DEFAULT_PRODUCT_ID)
        self.assertEqual(config.out_endpoint, DEFAULT_OUT_ENDPOINT)
        self.assertIsNone(config.presets_file)


if __name__ == "__main__":
    unittest.main()