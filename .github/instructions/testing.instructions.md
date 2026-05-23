---
applyTo: tests/**
---

# Testing Instructions

## Core Rule: Fakes Over Mocks

Construct a plain struct that satisfies the relevant `Protocol`. Do not use `MagicMock` unless there is genuinely no alternative.

```python
class FakeTransport:
    def __init__(self) -> None:
        self.payloads: list[bytes] = []

    def send_payload(self, payload: bytes) -> None:
        self.payloads.append(payload)
```

## Per-Layer Test Patterns

| Module under test | Dependency to fake | Where to inject |
|---|---|---|
| `client.py` | `FakeTransport` implementing `TransportProtocol` | `DnafxPresetClient(config, transport=fake)` |
| `listener.py` | `FakeMidiIn` implementing `MidiInputProtocol`; `FakeClient` implementing `PresetSwitchingClientProtocol` | `MidiProgramChangeListener(client, midi_in_factory=lambda: fake_midi)` |
| `cli.py` | patch `build_client` and/or `build_listener` factories | `patch("dnafx_preset.cli.build_client", return_value=fake)` |
| `config.py` | environment variables | `monkeypatch.setenv("DNAFX_VENDOR_ID", "0483")` |
| `transport.py` | inject device directly | `USBTransport(..., device=fake_device)` |

## Never Require Real Hardware

All USB and MIDI interaction is behind Protocol seams. Tests must never open a real USB device or MIDI port.

## Test File Structure

Use plain pytest functions — no `unittest.TestCase` for new tests:

```python
def test_descriptive_name() -> None:
    # arrange
    fake = FakeTransport()
    client = DnafxPresetClient(config, transport=fake)

    # act
    client.switch("1")

    # assert
    assert len(fake.payloads) == 1
```

## CLI Test Pattern

Patch the factory, not internals:

```python
def test_set_command() -> None:
    stdout = StringIO()
    with patch("dnafx_preset.cli.build_client", return_value=FakeClient()):
        exit_code = main(["set", "1"], stdout=stdout)
    assert exit_code == 0
```
