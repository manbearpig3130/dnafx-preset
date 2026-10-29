# GitHub Copilot Instructions

## Project

CLI and library for switching presets on a DNAfx GiT guitar processor over USB. Two commands: `set <slot>` sends a preset payload directly; `listen` opens a virtual MIDI input and bridges Program Change events to USB.

## Architecture

```
cli.py          argparse entrypoint — builds config, instantiates dependencies, dispatches commands
config.py       DeviceConfig and MidiListenerConfig — parse CLI args and env vars into frozen dataclasses
client.py       DnafxPresetClient — orchestrates catalog lookup + transport write
presets.py      PresetCatalog — maps slot numbers to byte payloads; PresetSelection is the result type
protocol.py     DNAfx message framing and CRC-16/GSM; preset_change_message() for slots 1–200
hid_transport.py  HIDTransport — default; wraps hidapi; opens the device for each write; no sudo
transport.py    USBTransport — wraps pyusb; lazy-loads the library; handles pipe-error recovery
listener.py     MidiProgramChangeListener — polls rtmidi for Program Change; maps channels/banks to slots
```

Each hardware dependency (`usb`, `rtmidi`) is hidden behind a `Protocol`:

| Protocol | Defined in | Implemented by |
|---|---|---|
| `TransportProtocol` | `transport.py` | `HIDTransport`, `USBTransport` |
| `MidiInputProtocol` | `listener.py` | `rtmidi.MidiIn` (at runtime) |
| `PresetSwitchingClientProtocol` | `listener.py` | `DnafxPresetClient` |
| `PresetCatalogProtocol` | `listener.py` | `PresetCatalog` |

## Design Invariants

- **Config types are frozen dataclasses.** `DeviceConfig` and `MidiListenerConfig` are immutable; never add mutable fields.
- **Result types are frozen dataclasses.** `PresetSelection` is returned from `catalog.resolve()` and `client.switch()`; callers must not mutate it.
- **Protocol-based seams.** Use `Protocol` (not `ABC`) for injectable dependencies so tests can pass plain structs without subclassing.
- **Slots are 1-based.** User-facing slot numbers start at 1. The catalog's internal list is 0-indexed but all public APIs use 1-based values.
- **USB IDs are hexadecimal.** `DNAFX_VENDOR_ID`, `DNAFX_PRODUCT_ID`, and `DNAFX_OUT_ENDPOINT` env vars are parsed as hex (with or without `0x`). Defaults: vendor `0x0483`, product `0x5703`, endpoint `0x02`.
- **`from __future__ import annotations` is present in every source file.** Do not wrap type annotations in quotes.

## MIDI Bank Mapping

Two consecutive MIDI channels form a bank pair covering all 200 slots:

```
slot = bank * 128 + program + 1

base channel  → bank 0 → slots 1–128   (programs 0–127)
base+1 channel → bank 1 → slots 129–200 (programs 0–71)
```

Programs that would exceed `slot_count` are silently ignored.

## Test Strategy

**Fakes over mocks.** Construct a plain struct that satisfies the relevant Protocol; do not use `MagicMock` unless there is no alternative.

| Module under test | What to fake |
|---|---|
| `client.py` | `FakeTransport` implementing `TransportProtocol` |
| `listener.py` | `FakeMidiIn` implementing `MidiInputProtocol`; `FakeClient` implementing `PresetSwitchingClientProtocol` |
| `cli.py` | patch `build_client` and/or `build_listener` factories; do not reach into internals |
| `config.py` | set env vars via `monkeypatch.setenv`; pass args as keyword arguments |

**Never require real USB or MIDI hardware.** All hardware interaction is behind the Protocol seam.

**Plain pytest functions.** No `unittest.TestCase` for new tests.

## Common Pitfalls

- The `usb` transport needs `brew install libusb` on macOS even though `pyusb` is in the dependencies, and `sudo`. The default `hid` transport needs neither.
- `DeviceConfig.from_sources()` always applies DNAfx GiT defaults for missing USB IDs; explicit values override them.
- `python-rtmidi` exposes `MidiIn` only on supported platforms; the listener raises `MidiListenerError` if it is absent.
