---
agent: ask
---

Add a new transport backend to `dnafx-preset` following the `USBTransport` pattern.

**Reference implementation:** `src/dnafx_preset/transport.py` and `tests/test_transport.py`.

## Steps

1. **Implement `TransportProtocol`** in a new file `src/dnafx_preset/my_transport.py`:
   ```python
   from __future__ import annotations
   from .transport import TransportProtocol  # only for type reference if needed

   class MyTransport:
       def send_payload(self, payload: bytes) -> None:
           # send payload to device
           ...
   ```
   The class does **not** need to subclass anything — it just needs to satisfy the structural protocol.

2. **Write a `Fake*` test double** in the test file:
   ```python
   class FakeMyDevice:
       def __init__(self) -> None:
           self.payloads: list[bytes] = []
       def write(self, payload: bytes) -> None:
           self.payloads.append(payload)
   ```

3. **Write tests** injecting the fake:
   ```python
   def test_send_payload_delegates_to_device() -> None:
       device = FakeMyDevice()
       transport = MyTransport(device=device)
       transport.send_payload(b"\x01\x02")
       assert device.payloads == [b"\x01\x02"]
   ```

4. **Expose via CLI** (optional) — if the transport should be selectable at runtime, add a flag in `build_client()` or a new factory function in `cli.py`, then patch it in CLI tests.

## Constraints

- Raise a subclass of `RuntimeError` (like `USBTransportError`) on unrecoverable errors, with actionable messages.
- Lazy-import the underlying library inside `connect()` or `send_payload()` — never at module import time — so the package installs without the dependency being present.
- Never require real hardware in tests; inject the device via constructor or a `device` parameter.
