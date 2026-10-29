from __future__ import annotations

from argparse import ArgumentParser, Namespace
from typing import Callable, Sequence, TextIO
import sys

from .client import DnafxPresetClient
from .config import (
    DEFAULT_OUT_ENDPOINT,
    DEFAULT_PRODUCT_ID,
    DEFAULT_TRANSPORT,
    DEFAULT_VENDOR_ID,
    TRANSPORTS,
    DeviceConfig,
    MidiListenerConfig,
)
from .listener import MidiProgramChangeListener
from .presets import PresetSelection
from .tone_map import ToneMap


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="dnafx-preset", description="DNAfx preset switcher")
    parser.add_argument(
        "--vendor-id",
        help=(
            "USB vendor ID in hexadecimal, for example 0483 "
            f"(default: {DEFAULT_VENDOR_ID:04x} for DNAfx GiT)"
        ),
    )
    parser.add_argument(
        "--product-id",
        help=(
            "USB product ID in hexadecimal, for example 5703 "
            f"(default: {DEFAULT_PRODUCT_ID:04x} for DNAfx GiT)"
        ),
    )
    parser.add_argument(
        "--out-endpoint",
        help=(
            "USB output endpoint in hexadecimal, for example 02 "
            f"(default: {DEFAULT_OUT_ENDPOINT:02x} for DNAfx GiT); only used by the usb transport"
        ),
    )
    parser.add_argument(
        "--transport",
        choices=TRANSPORTS,
        default=None,
        help=(
            "How to talk to the DNAfx: hid uses the operating system's HID driver and needs no sudo; "
            f"usb uses pyusb and libusb (default: {DEFAULT_TRANSPORT})"
        ),
    )
    parser.add_argument("--presets-file", help="Optional path to a custom preset JSON override")

    subparsers = parser.add_subparsers(dest="command", required=True)

    set_parser = subparsers.add_parser("set", help="Switch to a preset by slot number")
    set_parser.add_argument("target", help="1-based preset slot number")

    listen_parser = subparsers.add_parser("listen", help="Expose a virtual MIDI input and forward Program Change")
    listen_parser.add_argument(
        "--midi-channel",
        default=None,
        help="Raw base MIDI channel number, from 0 to 15; this channel selects slots 1-128 and the next channel selects slots 129-200 (default: 0)",
    )
    listen_parser.add_argument(
        "--midi-port-name",
        default=None,
        help="Virtual MIDI input port name (default: DNAfx Preset In)",
    )
    listen_parser.add_argument(
        "--midi-source",
        default=None,
        help=(
            "Instead of a virtual input, connect to the MIDI source whose name contains this text, "
            "for example 'Rocksmith Companion'; waits for it to appear and reconnects when it comes back"
        ),
    )
    listen_parser.add_argument(
        "--midi-program-map",
        default=None,
        help=(
            "Comma-separated PROGRAM=SLOT pairs for Program Change on the base channel, "
            "for example 0=49,1=50,2=51,3=187; other programs select slot program+1"
        ),
    )
    listen_parser.add_argument(
        "--config",
        default=None,
        help="TOML file with rules that pick a slot for each tone RS Companion's song tone messages describe",
    )

    return parser


def build_config(args: Namespace) -> DeviceConfig:
    return DeviceConfig.from_sources(
        vendor_id=args.vendor_id,
        product_id=args.product_id,
        out_endpoint=args.out_endpoint,
        presets_file=args.presets_file,
        transport=args.transport,
    )


def build_client(args: Namespace) -> DnafxPresetClient:
    return DnafxPresetClient(build_config(args))


def build_listener_config(args: Namespace) -> MidiListenerConfig:
    return MidiListenerConfig.from_sources(
        channel=args.midi_channel,
        port_name=args.midi_port_name,
        source_name=args.midi_source,
        program_map=args.midi_program_map,
        config_file=args.config,
    )


def build_listener(
    args: Namespace,
    error_handler: Callable[[Exception], None] | None = None,
    status_handler: Callable[[str], None] | None = None,
) -> MidiProgramChangeListener:
    listener_config = build_listener_config(args)
    return MidiProgramChangeListener(
        build_client(args),
        channel=listener_config.channel,
        port_name=listener_config.port_name,
        source_name=listener_config.source_name,
        program_map=listener_config.program_map,
        tone_map=ToneMap.load(listener_config.config_file) if listener_config.config_file is not None else None,
        error_handler=error_handler,
        status_handler=status_handler,
    )


def format_selection(selection: PresetSelection) -> str:
    return f"slot {selection.slot_number}"


def handle_switch(args: Namespace, stdout: TextIO) -> int:
    client = build_client(args)
    selection = client.switch(args.target)
    stdout.write(f"Switched to {format_selection(selection)}\n")
    return 0


def handle_listen(args: Namespace, stdout: TextIO, stderr: TextIO) -> int:
    def report_error(exc: Exception) -> None:
        stderr.write(f"Error: {exc}\n")

    def report_status(message: str) -> None:
        stdout.write(f"{message}\n")
        stdout.flush()

    listener = build_listener(args, report_error, report_status)
    channel_text = f"raw channel {listener.channel}"
    if listener.channel < 15:
        channel_text = f"raw channels {listener.channel} and {listener.channel + 1}"

    if listener.source_name is None:
        stdout.write(f"Listening on virtual MIDI input '{listener.port_name}' for Program Change on {channel_text}\n")
    else:
        stdout.write(f"Listening to MIDI source '{listener.source_name}' for Program Change on {channel_text}\n")
    stdout.flush()
    listener.listen()
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    resolved_stdout: TextIO = stdout if stdout is not None else sys.stdout
    resolved_stderr: TextIO = stderr if stderr is not None else sys.stderr

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "set":
            return handle_switch(args, resolved_stdout)
        if args.command == "listen":
            return handle_listen(args, resolved_stdout, resolved_stderr)
    except Exception as exc:
        resolved_stderr.write(f"Error: {exc}\n")
        return 1

    parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())