# dnafx-preset

`dnafx-preset` is a standalone Python library and CLI for switching presets on a DNAfx device.

When run in listener mode, it also exposes a virtual MIDI input port to macOS and translates incoming Program Change messages into DNAfx preset changes.

## Scope

- Switch to a preset by numeric slot.
- Listen on a virtual MIDI input and map MIDI Program Change to preset slots.

## Install

```bash
pip install ./dnafx-preset
```

On macOS, `pyusb` also needs a system `libusb` backend:

```bash
brew install libusb
```

## Configuration

The USB settings can be provided either through CLI flags or environment variables.

- `DNAFX_VENDOR_ID`
- `DNAFX_PRODUCT_ID`
- `DNAFX_OUT_ENDPOINT`
- `DNAFX_PRESETS_FILE` (optional override)

If you do not provide the USB values, `dnafx-preset` uses built-in defaults for the DNAfx GiT device:

- `DNAFX_VENDOR_ID=0483`
- `DNAFX_PRODUCT_ID=5703`
- `DNAFX_OUT_ENDPOINT=02`

By default, the package uses an embedded numeric preset table. `DNAFX_PRESETS_FILE` is only needed if you want to override that default mapping with a custom JSON file.

The USB values are parsed as hexadecimal, so the current device values can be passed as `0483`, `5703`, or `0x02`.

If you see `No USB backend available`, `libusb` is missing from the system even if the Python package installed correctly.

If you see `Access denied` or the CLI tells you it could not claim the USB interface, rerun the preset command with `sudo`. The original server code also expected elevated privileges for USB writes.

## MIDI Listener

The `listen` command creates a virtual MIDI input port while the process is running. Other MIDI-capable apps on macOS can send to that port, and the app will forward accepted messages to the DNAfx device.

- Default virtual port name: `DNAfx Preset In`
- Default base listen channel: raw MIDI channel `0` (user-facing MIDI channel 1)
- Supported messages: Program Change on the base channel or the next channel

Slot mapping is zero-based internally and converted to DNAfx slot numbers as:

```text
slot = bank * 128 + program + 1
```

Where:

- Program Change on the configured base channel selects bank `0`, covering DNAfx slots `1..128`
- Program Change on the next raw MIDI channel selects bank `1`, covering DNAfx slots `129..201`

That means:

- Channel `0`, Program `0` selects DNAfx slot `1`
- Channel `0`, Program `127` selects DNAfx slot `128`
- Channel `1`, Program `0` selects DNAfx slot `129`

With a non-default base channel, the same rule still applies: base channel for the lower bank, next channel for the upper bank. Out-of-range bank and program combinations are ignored.

## Examples

```bash
dnafx-preset set 1
sudo dnafx-preset set 1
sudo dnafx-preset listen
sudo dnafx-preset listen --midi-channel 0 --midi-port-name "DNAfx Preset In"
dnafx-preset --vendor-id 0483 --product-id 5703 --out-endpoint 02 set 1
sudo dnafx-preset --vendor-id 0483 --product-id 5703 --out-endpoint 02 set 1
sudo dnafx-preset --vendor-id 0483 --product-id 5703 --out-endpoint 02 listen
sudo dnafx-preset --vendor-id 0483 --product-id 5703 --out-endpoint 02 listen --midi-channel 0 --midi-port-name "DNAfx Preset In"
```

## Development

```bash
pip install -e ".[test]"
python -m pytest
```