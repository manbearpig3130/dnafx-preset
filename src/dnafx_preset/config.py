from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


ENV_VENDOR_ID = "DNAFX_VENDOR_ID"
ENV_PRODUCT_ID = "DNAFX_PRODUCT_ID"
ENV_OUT_ENDPOINT = "DNAFX_OUT_ENDPOINT"
ENV_PRESETS_FILE = "DNAFX_PRESETS_FILE"
ENV_MIDI_CHANNEL = "DNAFX_MIDI_CHANNEL"
ENV_MIDI_PORT_NAME = "DNAFX_MIDI_PORT_NAME"


def parse_hex_int(value: str | int | None, *, field_name: str) -> int:
    if isinstance(value, int):
        return value
    if value is None:
        raise ValueError(f"Missing required value for {field_name}")

    raw_value = value.strip()
    if not raw_value:
        raise ValueError(f"Missing required value for {field_name}")

    try:
        return int(raw_value, 16)
    except ValueError as exc:
        raise ValueError(f"Invalid hexadecimal value for {field_name}: {value}") from exc


def parse_int(value: str | int | None, *, field_name: str) -> int:
    if isinstance(value, int):
        return value
    if value is None:
        raise ValueError(f"Missing required value for {field_name}")

    raw_value = value.strip()
    if not raw_value:
        raise ValueError(f"Missing required value for {field_name}")

    try:
        return int(raw_value, 10)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value for {field_name}: {value}") from exc


@dataclass(frozen=True)
class DeviceConfig:
    vendor_id: int | None
    product_id: int | None
    out_endpoint: int | None
    presets_file: Path | None

    @classmethod
    def from_sources(
        cls,
        *,
        vendor_id: str | int | None = None,
        product_id: str | int | None = None,
        out_endpoint: str | int | None = None,
        presets_file: str | os.PathLike[str] | None = None,
        require_usb: bool = True,
    ) -> "DeviceConfig":
        env_vendor = os.environ.get(ENV_VENDOR_ID)
        env_product = os.environ.get(ENV_PRODUCT_ID)
        env_endpoint = os.environ.get(ENV_OUT_ENDPOINT)
        env_presets = os.environ.get(ENV_PRESETS_FILE)

        resolved_vendor = vendor_id if vendor_id is not None else env_vendor
        resolved_product = product_id if product_id is not None else env_product
        resolved_endpoint = out_endpoint if out_endpoint is not None else env_endpoint

        if require_usb:
            vendor_value = parse_hex_int(resolved_vendor, field_name=ENV_VENDOR_ID)
            product_value = parse_hex_int(resolved_product, field_name=ENV_PRODUCT_ID)
            endpoint_value = parse_hex_int(resolved_endpoint, field_name=ENV_OUT_ENDPOINT)
        else:
            vendor_value = parse_hex_int(resolved_vendor, field_name=ENV_VENDOR_ID) if resolved_vendor else None
            product_value = parse_hex_int(resolved_product, field_name=ENV_PRODUCT_ID) if resolved_product else None
            endpoint_value = parse_hex_int(resolved_endpoint, field_name=ENV_OUT_ENDPOINT) if resolved_endpoint else None

        resolved_presets_source = presets_file if presets_file is not None else env_presets
        resolved_presets = Path(resolved_presets_source).expanduser() if resolved_presets_source is not None else None

        return cls(
            vendor_id=vendor_value,
            product_id=product_value,
            out_endpoint=endpoint_value,
            presets_file=resolved_presets,
        )


@dataclass(frozen=True)
class MidiListenerConfig:
    channel: int
    port_name: str

    @classmethod
    def from_sources(
        cls,
        *,
        channel: str | int | None = None,
        port_name: str | None = None,
    ) -> "MidiListenerConfig":
        env_channel = os.environ.get(ENV_MIDI_CHANNEL)
        env_port_name = os.environ.get(ENV_MIDI_PORT_NAME)

        resolved_channel = channel if channel is not None else env_channel
        resolved_port_name = port_name if port_name is not None else env_port_name

        channel_value = 0 if resolved_channel is None else parse_int(resolved_channel, field_name=ENV_MIDI_CHANNEL)
        if channel_value < 0 or channel_value > 15:
            raise ValueError("MIDI channel must be between 0 and 15")

        port_value = (resolved_port_name or "DNAfx Preset In").strip()
        if not port_value:
            raise ValueError("MIDI port name cannot be empty")

        return cls(channel=channel_value, port_name=port_value)