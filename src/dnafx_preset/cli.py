from __future__ import annotations

from argparse import ArgumentParser, Namespace
from typing import Callable, Sequence, TextIO
import sys

from .client import DnafxPresetClient
from .config import DEFAULT_OUT_ENDPOINT, DEFAULT_PRODUCT_ID, DEFAULT_VENDOR_ID, DeviceConfig, MidiListenerConfig
from .listener import MidiProgramChangeListener
from .presets import PresetSelection


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
            f"(default: {DEFAULT_OUT_ENDPOINT:02x} for DNAfx GiT)"
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
        help="Raw base MIDI channel number, from 0 to 15; this channel selects slots 1-128 and the next channel selects slots 129-201 (default: 0)",
    )
    listen_parser.add_argument(
        "--midi-port-name",
        default=None,
        help="Virtual MIDI input port name (default: DNAfx Preset In)",
    )

    return parser


def build_config(args: Namespace) -> DeviceConfig:
    return DeviceConfig.from_sources(
        vendor_id=args.vendor_id,
        product_id=args.product_id,
        out_endpoint=args.out_endpoint,
        presets_file=args.presets_file,
    )


def build_client(args: Namespace) -> DnafxPresetClient:
    return DnafxPresetClient(build_config(args))


def build_listener_config(args: Namespace) -> MidiListenerConfig:
    return MidiListenerConfig.from_sources(channel=args.midi_channel, port_name=args.midi_port_name)


def build_listener(
    args: Namespace,
    error_handler: Callable[[Exception], None] | None = None,
) -> MidiProgramChangeListener:
    listener_config = build_listener_config(args)
    return MidiProgramChangeListener(
        build_client(args),
        channel=listener_config.channel,
        port_name=listener_config.port_name,
        error_handler=error_handler,
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

    listener = build_listener(args, report_error)
    channel_text = f"raw channel {listener.channel}"
    if listener.channel < 15:
        channel_text = f"raw channels {listener.channel} and {listener.channel + 1}"

    stdout.write(f"Listening on virtual MIDI input '{listener.port_name}' for Program Change on {channel_text}\n")
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