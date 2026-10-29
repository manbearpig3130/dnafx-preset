# AGENTS.md

## Start Here

- Read [README.md](README.md) for device defaults, CLI examples, and MIDI listener behavior.
- Use Python 3.11+.
- Install test tooling with `pip install -e ".[test]"`.
- Run the full test suite with `python -m pytest`.
- Run type checking with `pyright src/`.
- For focused local runs, use `python -m pytest tests/test_cli.py tests/test_config.py`.

## Working Rules

- Use `pytest` as the test runner. Write new tests as plain pytest functions — not `unittest.TestCase`.
- Avoid tests that require real USB or MIDI hardware. Follow the existing seams: patch the factories in `cli.py` and use protocol-compatible fakes.
- Preserve the current design choices: frozen dataclasses for configuration/result types and protocol-based abstractions for transport and MIDI dependencies.
- Treat preset slots as 1-based user-facing values. MIDI mapping stays `slot = bank * 128 + program + 1`.
- Do not wrap type annotations in quotes — `from __future__ import annotations` is present in every source file.

## Architecture

- `src/dnafx_preset/cli.py`: argparse entrypoint and command routing for `set` and `listen`.
- `src/dnafx_preset/config.py`: CLI and environment parsing for USB and MIDI settings.
- `src/dnafx_preset/client.py`: preset-switching orchestration.
- `src/dnafx_preset/hid_transport.py`: HID transport (default; hidapi, no sudo).
- `src/dnafx_preset/transport.py`: USB transport wrapper (pyusb).
- `src/dnafx_preset/listener.py`: MIDI listener on a virtual input or another app's MIDI source.
- `src/dnafx_preset/presets.py`: preset catalog and JSON override loading.
- `src/dnafx_preset/protocol.py`: DNAfx message framing, CRC and the preset change message.

## Test Patterns

| Module under test | What to fake | How to inject |
|---|---|---|
| `client.py` | `FakeTransport` implementing `TransportProtocol` | `DnafxPresetClient(config, transport=fake)` |
| `listener.py` | `FakeMidiIn` + `FakeClient` | `MidiProgramChangeListener(client, midi_in_factory=lambda: fake)` |
| `cli.py` | patch `build_client` and/or `build_listener` | `patch("dnafx_preset.cli.build_client", return_value=fake)` |
| `config.py` | env vars | `monkeypatch.setenv(...)` |
| `transport.py` | inject device directly | `USBTransport(..., device=fake_device)` |
| `hid_transport.py` | `FakeHIDDevice` | `HIDTransport(..., device_factory=lambda: fake_device)` |

## How to Extend

### Add a new CLI command
1. Add a subparser in `build_parser()`.
2. Add a `handle_*()` function taking `(args: Namespace, stdout: TextIO) -> int`.
3. Wire it into the `main()` dispatch block.
4. Write a test patching `build_client` or `build_listener` — never internal methods.
See `.github/prompts/add-command.prompt.md` for the full recipe.

### Add a new transport backend
1. Implement `TransportProtocol` in a new module (no subclassing needed).
2. Add a `Fake*` test double for the underlying device.
3. Lazy-import the hardware library inside `send_payload()` or a `connect()` method.
See `.github/prompts/add-transport.prompt.md` for the full recipe.

### Add a custom preset source
1. Load the source into a `dict[str, object]` mapping numeric string keys to byte-value lists.
2. Pass it to `PresetCatalog._from_dict()` or write a new `_from_*` classmethod if the format differs.
3. Wire the source selection through `DeviceConfig.presets_file` or a new config field.

## Project Pitfalls

- The `usb` transport needs `libusb` (`brew install libusb` on macOS; `pyusb` alone is not enough) and, on macOS, `sudo`. The default `hid` transport needs neither.
- The DNAfx has 200 slots. Preset change messages are computed in `protocol.py`; don't add byte tables.
- Use `pip install -e ".[test]"` before running `pytest` in a fresh environment.
- `DNAFX_VENDOR_ID`, `DNAFX_PRODUCT_ID`, and `DNAFX_OUT_ENDPOINT` are parsed as hexadecimal values, with or without an `0x` prefix.
- `DNAFX_PRESETS_FILE` is optional; the computed preset change messages are the default.
- `DeviceConfig.from_sources()` always applies DNAfx GiT defaults when USB IDs are omitted.