# dnafx-preset

`dnafx-preset` is a standalone Python library and CLI for switching presets on a DNAfx device.

When run in listener mode, it also exposes a virtual MIDI input port to macOS, or connects to another app's MIDI source, and translates incoming Program Change messages into DNAfx preset changes.

## Scope

- Switch to a preset by numeric slot.
- Listen on a virtual MIDI input, or on another app's MIDI source, and map MIDI Program Change to preset slots.

## Install

```bash
pip install ./dnafx-preset
```

Connect the DNAfx's USB-B port to the computer. The USB-C port only carries audio.

## Transports

- `hid` (default) talks to the DNAfx through the operating system's HID driver, using `hidapi`. It needs no `sudo` and no `libusb`. It opens the device only for the moment it sends a preset change, so the Harley Benton editor can stay open alongside it. Tested on macOS.
- `usb` talks to the DNAfx with `pyusb`, which detaches the HID driver first. On macOS it needs `brew install libusb` and `sudo`.

Choose one with `--transport` or `DNAFX_TRANSPORT`.

## Configuration

The USB settings can be provided either through CLI flags or environment variables.

- `DNAFX_VENDOR_ID`
- `DNAFX_PRODUCT_ID`
- `DNAFX_OUT_ENDPOINT` (`usb` transport only)
- `DNAFX_TRANSPORT` (`hid` or `usb`, default `hid`)
- `DNAFX_PRESETS_FILE` (optional override)

If you do not provide the USB values, `dnafx-preset` uses built-in defaults for the DNAfx GiT device:

- `DNAFX_VENDOR_ID=0483`
- `DNAFX_PRODUCT_ID=5703`
- `DNAFX_OUT_ENDPOINT=02`

By default, the package builds the preset change message for each of the DNAfx's 200 slots (P001 to P200): one 64-byte packet with command `0x96`, the slot number and a CRC-16/GSM checksum, as documented by [lminiero/dnafx-editor](https://github.com/lminiero/dnafx-editor). `DNAFX_PRESETS_FILE` is only needed if you want to override that default mapping with a custom JSON file.

The USB values are parsed as hexadecimal, so the current device values can be passed as `0483`, `5703`, or `0x02`.

With the `usb` transport, `No USB backend available` means `libusb` is missing from the system even if the Python package installed correctly, and `Access denied` means the command needs `sudo`.

## MIDI Listener

The `listen` command creates a virtual MIDI input port while the process is running. Other MIDI-capable apps on macOS can send to that port, and the app will forward accepted messages to the DNAfx device.

Apps that publish their own MIDI source instead of sending to a port, such as RS Companion, need `--midi-source NAME` (or `DNAFX_MIDI_SOURCE`). The listener then connects to the first MIDI source whose name contains `NAME` (ignoring case), waits for it if it doesn't exist yet, and connects again when the app quits and starts again.

- Default virtual port name: `DNAfx Preset In`
- Default base listen channel: raw MIDI channel `0` (user-facing MIDI channel 1)
- Supported messages: Program Change on the base channel or the next channel

Slot mapping is zero-based internally and converted to DNAfx slot numbers as:

```text
slot = bank * 128 + program + 1
```

Where:

- Program Change on the configured base channel selects bank `0`, covering DNAfx slots `1..128`
- Program Change on the next raw MIDI channel selects bank `1`, covering DNAfx slots `129..200`

That means:

- Channel `0`, Program `0` selects DNAfx slot `1`
- Channel `0`, Program `127` selects DNAfx slot `128`
- Channel `1`, Program `0` selects DNAfx slot `129`

With a non-default base channel, the same rule still applies: base channel for the lower bank, next channel for the upper bank. Out-of-range bank and program combinations are ignored.

`--midi-program-map` (or `DNAFX_MIDI_PROGRAM_MAP`) maps programs on the base channel to any slot instead, as comma-separated `PROGRAM=SLOT` pairs. Programs without an entry keep the rule above. For example, `0=49,3=187` makes program `0` select slot `49` and program `3` select slot `187`, which a single channel can't reach otherwise.

## Rocksmith with RS Companion

[RS Companion](https://github.com/glebb/rs-mac-companion) sends a Program Change on its MIDI source `Rocksmith Companion` when Rocksmith's tone changes category (Clean, Crunch, Heavy, Lead):

```bash
dnafx-preset listen --midi-source "Rocksmith Companion"
```

With RS Companion's default program numbers (Clean 0, Crunch 1, Heavy 2, Lead 3, on MIDI channel 1), map each category to a DNAfx slot:

```bash
dnafx-preset listen --midi-source "Rocksmith Companion" --midi-program-map 0=49,1=50,2=51,3=187
```

This selects P049 for Clean, P050 for Crunch, P051 for Heavy and P187 for Lead.

## Examples

```bash
dnafx-preset set 1
dnafx-preset listen
dnafx-preset listen --midi-channel 0 --midi-port-name "DNAfx Preset In"
dnafx-preset listen --midi-source "Rocksmith Companion"
dnafx-preset listen --midi-source "Rocksmith Companion" --midi-program-map 0=49,1=50,2=51,3=187
dnafx-preset --vendor-id 0483 --product-id 5703 set 1
sudo dnafx-preset --transport usb --vendor-id 0483 --product-id 5703 --out-endpoint 02 set 1
```

## Development

```bash
pip install -e ".[test]"
python -m pytest
```