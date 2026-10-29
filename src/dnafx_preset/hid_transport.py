from __future__ import annotations

from typing import Callable, Protocol, cast

from .protocol import PACKET_SIZE


class HIDDeviceProtocol(Protocol):
    def open(self, vendor_id: int, product_id: int) -> None:
        ...

    def write(self, buff: bytes) -> int:
        ...

    def close(self) -> None:
        ...


class HIDTransportError(RuntimeError):
    pass


class HIDTransport:
    # The DNAfx control port is a HID device with 64-byte reports and no report IDs, so the
    # operating system's HID driver can talk to it: no libusb and no sudo. The device is opened
    # for each write and closed again. On macOS hidapi opens devices exclusively, so holding it
    # open would lock out the Harley Benton editor; reopening also survives unplugging the DNAfx.

    def __init__(
        self,
        *,
        vendor_id: int,
        product_id: int,
        device_factory: Callable[[], HIDDeviceProtocol] | None = None,
    ):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self._device_factory = device_factory or self._default_device_factory

    def send_payload(self, payload: bytes) -> None:
        if len(payload) > PACKET_SIZE:
            raise HIDTransportError(f"Payload is {len(payload)} bytes; the DNAfx takes at most {PACKET_SIZE}")

        # Report ID 0 (the device has none), then the packet padded to the report size
        report = b"\x00" + payload.ljust(PACKET_SIZE, b"\x00")
        device = self._device_factory()
        try:
            device.open(self.vendor_id, self.product_id)
        except OSError as exc:
            raise HIDTransportError(self._not_found_message()) from exc

        try:
            written = device.write(report)
        except (OSError, ValueError) as exc:
            raise HIDTransportError(f"Unable to write to the DNAfx HID device: {exc}") from exc
        finally:
            device.close()

        if written < 0:
            raise HIDTransportError("Unable to write to the DNAfx HID device. Reconnect it and rerun the command.")

    def _not_found_message(self) -> str:
        return (
            f"DNAfx device {self.vendor_id:04x}:{self.product_id:04x} was not found or could not be opened. "
            "Connect the DNAfx's USB-B port (USB-C only carries audio), check DNAFX_VENDOR_ID and "
            "DNAFX_PRODUCT_ID, and rerun the command."
        )

    @staticmethod
    def _default_device_factory() -> HIDDeviceProtocol:
        try:
            import hid
        except ImportError as exc:
            raise HIDTransportError(
                "hidapi is required for the HID transport. Install it with 'pip install hidapi', "
                "or use --transport usb."
            ) from exc

        return cast(HIDDeviceProtocol, hid.device())
