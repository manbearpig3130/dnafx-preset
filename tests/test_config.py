import os
from pathlib import Path
from unittest.mock import patch

import pytest
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


def test_program_map_defaults_to_empty(monkeypatch) -> None:
    monkeypatch.delenv("DNAFX_MIDI_PROGRAM_MAP", raising=False)

    assert MidiListenerConfig.from_sources().program_map == ()


def test_parses_program_map() -> None:
    config = MidiListenerConfig.from_sources(program_map=" 0=49, 1=50,2 = 51,3=187, ")

    assert config.program_map == ((0, 49), (1, 50), (2, 51), (3, 187))


def test_program_map_comes_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DNAFX_MIDI_PROGRAM_MAP", "3=187")

    assert MidiListenerConfig.from_sources().program_map == ((3, 187),)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("0:49", "PROGRAM=SLOT"),
        ("x=49", "Invalid integer value"),
        ("128=1", "between 0 and 127"),
        ("0=0", "at least 1"),
        ("0=49,0=50", "mapped more than once"),
    ],
)
def test_rejects_invalid_program_maps(value: str, message: str) -> None:
    with raises(ValueError, match=message):
        MidiListenerConfig.from_sources(program_map=value)


def test_config_file_comes_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DNAFX_CONFIG", "~/tones.toml")

    assert MidiListenerConfig.from_sources().config_file == Path("~/tones.toml").expanduser()


def test_config_file_defaults_to_none(monkeypatch) -> None:
    monkeypatch.delenv("DNAFX_CONFIG", raising=False)

    assert MidiListenerConfig.from_sources().config_file is None
