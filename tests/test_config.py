import os
from unittest.mock import patch

from pytest import raises

from dnafx_preset.config import (
    DEFAULT_OUT_ENDPOINT,
    DEFAULT_PRODUCT_ID,
    DEFAULT_VENDOR_ID,
    DeviceConfig,
    MidiListenerConfig,
)


def test_uses_dnafx_git_defaults_when_usb_values_are_missing() -> None:
    with patch.dict(os.environ, {}, clear=True):
        config = DeviceConfig.from_sources()

    assert config.vendor_id == DEFAULT_VENDOR_ID
    assert config.product_id == DEFAULT_PRODUCT_ID
    assert config.out_endpoint == DEFAULT_OUT_ENDPOINT
    assert config.presets_file is None
    assert config.transport == "hid"


def test_transport_comes_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DNAFX_TRANSPORT", "USB")

    assert DeviceConfig.from_sources().transport == "usb"


def test_transport_argument_overrides_environment(monkeypatch) -> None:
    monkeypatch.setenv("DNAFX_TRANSPORT", "usb")

    assert DeviceConfig.from_sources(transport="hid").transport == "hid"


def test_rejects_unknown_transport() -> None:
    with raises(ValueError, match="Transport must be one of hid, usb"):
        DeviceConfig.from_sources(transport="serial")


def test_midi_source_defaults_to_none(monkeypatch) -> None:
    monkeypatch.delenv("DNAFX_MIDI_SOURCE", raising=False)

    assert MidiListenerConfig.from_sources().source_name is None


def test_midi_source_comes_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DNAFX_MIDI_SOURCE", " Rocksmith Companion ")

    assert MidiListenerConfig.from_sources().source_name == "Rocksmith Companion"


def test_rejects_empty_midi_source() -> None:
    with raises(ValueError, match="MIDI source name cannot be empty"):
        MidiListenerConfig.from_sources(source_name="  ")
