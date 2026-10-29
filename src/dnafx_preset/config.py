from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


ENV_VENDOR_ID = "DNAFX_VENDOR_ID"
ENV_PRODUCT_ID = "DNAFX_PRODUCT_ID"
ENV_OUT_ENDPOINT = "DNAFX_OUT_ENDPOINT"
ENV_PRESETS_FILE = "DNAFX_PRESETS_FILE"
ENV_TRANSPORT = "DNAFX_TRANSPORT"
ENV_MIDI_CHANNEL = "DNAFX_MIDI_CHANNEL"
ENV_MIDI_PORT_NAME = "DNAFX_MIDI_PORT_NAME"
ENV_MIDI_SOURCE = "DNAFX_MIDI_SOURCE"
ENV_MIDI_PROGRAM_MAP = "DNAFX_MIDI_PROGRAM_MAP"
ENV_CONFIG = "DNAFX_CONFIG"

DEFAULT_VENDOR_ID = 0x0483
DEFAULT_PRODUCT_ID = 0x5703
DEFAULT_OUT_ENDPOINT = 0x02
TRANSPORTS = ("hid", "usb")
DEFAULT_TRANSPORT = "hid"


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


def parse_program_map(value: str | None) -> tuple[tuple[int, int], ...]:
    # "0=49, 1=50" -> ((0, 49), (1, 50)): MIDI program (0-127) to 1-based slot
    if value is None:
        return ()

    pairs: list[tuple[int, int]] = []
    for entry in value.split(","):
        if not entry.strip():
            continue
        program_text, separator, slot_text = entry.partition("=")
        if not separator:
            raise ValueError(f"{ENV_MIDI_PROGRAM_MAP} entries must look like PROGRAM=SLOT: {entry.strip()}")

        program = parse_int(program_text, field_name=ENV_MIDI_PROGRAM_MAP)
        slot_number = parse_int(slot_text, field_name=ENV_MIDI_PROGRAM_MAP)
        if program < 0 or program > 127:
            raise ValueError(f"MIDI program must be between 0 and 127: {program}")
        if slot_number < 1:
            raise ValueError(f"Slot must be at least 1: {slot_number}")
        if any(program == mapped for mapped, _slot in pairs):
            raise ValueError(f"MIDI program {program} is mapped more than once")
        pairs.append((program, slot_number))

    return tuple(pairs)


@dataclass(frozen=True)
class DeviceConfig:
    vendor_id: int
    product_id: int
    out_endpoint: int
    presets_file: Path | None
    transport: str = DEFAULT_TRANSPORT

    @classmethod
    def from_sources(
        cls,
        *,
        vendor_id: str | int | None = None,
        product_id: str | int | None = None,
        out_endpoint: str | int | None = None,
        presets_file: str | os.PathLike[str] | None = None,
        transport: str | None = None,
    ) -> DeviceConfig:
        env_vendor = os.environ.get(ENV_VENDOR_ID)
        env_product = os.environ.get(ENV_PRODUCT_ID)
        env_endpoint = os.environ.get(ENV_OUT_ENDPOINT)
        env_presets = os.environ.get(ENV_PRESETS_FILE)
        env_transport = os.environ.get(ENV_TRANSPORT)

        resolved_vendor = vendor_id if vendor_id is not None else env_vendor
        resolved_product = product_id if product_id is not None else env_product
        resolved_endpoint = out_endpoint if out_endpoint is not None else env_endpoint

        resolved_vendor = DEFAULT_VENDOR_ID if resolved_vendor is None else resolved_vendor
        resolved_product = DEFAULT_PRODUCT_ID if resolved_product is None else resolved_product
        resolved_endpoint = DEFAULT_OUT_ENDPOINT if resolved_endpoint is None else resolved_endpoint

        vendor_value = parse_hex_int(resolved_vendor, field_name=ENV_VENDOR_ID)
        product_value = parse_hex_int(resolved_product, field_name=ENV_PRODUCT_ID)
        endpoint_value = parse_hex_int(resolved_endpoint, field_name=ENV_OUT_ENDPOINT)

        resolved_presets_source = presets_file if presets_file is not None else env_presets
        resolved_presets = Path(resolved_presets_source).expanduser() if resolved_presets_source is not None else None

        resolved_transport = transport if transport is not None else env_transport
        transport_value = (resolved_transport or DEFAULT_TRANSPORT).strip().lower()
        if transport_value not in TRANSPORTS:
            raise ValueError(f"Transport must be one of {', '.join(TRANSPORTS)}: {resolved_transport}")

        return cls(
            vendor_id=vendor_value,
            product_id=product_value,
            out_endpoint=endpoint_value,
            presets_file=resolved_presets,
            transport=transport_value,
        )


@dataclass(frozen=True)
class MidiListenerConfig:
    channel: int
    port_name: str
    source_name: str | None = None
    program_map: tuple[tuple[int, int], ...] = ()
    config_file: Path | None = None

    @classmethod
    def from_sources(
        cls,
        *,
        channel: str | int | None = None,
        port_name: str | None = None,
        source_name: str | None = None,
        program_map: str | None = None,
        config_file: str | os.PathLike[str] | None = None,
    ) -> MidiListenerConfig:
        env_channel = os.environ.get(ENV_MIDI_CHANNEL)
        env_port_name = os.environ.get(ENV_MIDI_PORT_NAME)
        env_source_name = os.environ.get(ENV_MIDI_SOURCE)
        env_program_map = os.environ.get(ENV_MIDI_PROGRAM_MAP)
        env_config_file = os.environ.get(ENV_CONFIG)

        resolved_channel = channel if channel is not None else env_channel
        resolved_port_name = port_name if port_name is not None else env_port_name
        resolved_source_name = source_name if source_name is not None else env_source_name

        channel_value = 0 if resolved_channel is None else parse_int(resolved_channel, field_name=ENV_MIDI_CHANNEL)
        if channel_value < 0 or channel_value > 15:
            raise ValueError("MIDI channel must be between 0 and 15")

        port_value = (resolved_port_name or "DNAfx Preset In").strip()
        if not port_value:
            raise ValueError("MIDI port name cannot be empty")

        source_value = resolved_source_name.strip() if resolved_source_name is not None else None
        if source_value == "":
            raise ValueError("MIDI source name cannot be empty")

        program_map_value = parse_program_map(program_map if program_map is not None else env_program_map)

        resolved_config_file = config_file if config_file is not None else env_config_file
        config_file_value = Path(resolved_config_file).expanduser() if resolved_config_file else None

        return cls(
            channel=channel_value,
            port_name=port_value,
            source_name=source_value,
            program_map=program_map_value,
            config_file=config_file_value,
        )