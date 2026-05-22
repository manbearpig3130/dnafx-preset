# AGENTS.md

## Start Here

- Read [README.md](README.md) for device defaults, CLI examples, and MIDI listener behavior.
- Use Python 3.11+.
- Install test tooling with `pip install -e ".[test]"`.
- Run the full test suite with `python -m pytest`.
- For focused local runs, use `python -m pytest tests/test_cli.py tests/test_config.py`.

## Working Rules

- Use `pytest` as the test runner. Existing tests can stay on `unittest.TestCase` where that keeps changes small.
- Avoid tests that require real USB or MIDI hardware. Follow the existing seams: patch the factories in `cli.py` and use protocol-compatible fakes or mocks.
- Preserve the current design choices: frozen dataclasses for configuration/result types and protocol-based abstractions for transport and MIDI dependencies.
- Treat preset slots as 1-based user-facing values. MIDI mapping stays `slot = bank * 128 + program + 1`.

## Architecture

- `src/dnafx_preset/cli.py`: argparse entrypoint and command routing for `set` and `listen`.
- `src/dnafx_preset/config.py`: CLI and environment parsing for USB and MIDI settings.
- `src/dnafx_preset/client.py`: preset-switching orchestration.
- `src/dnafx_preset/transport.py`: USB transport wrapper.
- `src/dnafx_preset/listener.py`: virtual MIDI input listener.
- `src/dnafx_preset/presets.py`: preset catalog and JSON override loading.
- `src/dnafx_preset/embedded_presets.py`: built-in default preset payloads.

## Project Pitfalls

- On macOS, install `libusb` separately with `brew install libusb`; `pyusb` alone is not enough.
- Real USB writes may require `sudo`.
- Use `pip install -e ".[test]"` before running `pytest` in a fresh environment.
- `DNAFX_VENDOR_ID`, `DNAFX_PRODUCT_ID`, and `DNAFX_OUT_ENDPOINT` are parsed as hexadecimal values, with or without an `0x` prefix.
- `DNAFX_PRESETS_FILE` is optional; the embedded preset table is the default.