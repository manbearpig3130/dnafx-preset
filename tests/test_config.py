import os
from unittest.mock import patch

from pytest import raises

from dnafx_preset.config import DEFAULT_OUT_ENDPOINT, DEFAULT_PRODUCT_ID, DEFAULT_VENDOR_ID, DeviceConfig


def test_uses_dnafx_git_defaults_when_usb_values_are_missing() -> None:
    with patch.dict(os.environ, {}, clear=True):
        config = DeviceConfig.from_sources()

    assert config.vendor_id == DEFAULT_VENDOR_ID
    assert config.product_id == DEFAULT_PRODUCT_ID
    assert config.out_endpoint == DEFAULT_OUT_ENDPOINT
    assert config.presets_file is None