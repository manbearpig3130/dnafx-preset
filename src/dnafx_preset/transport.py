from __future__ import annotations

import sys
from collections.abc import Iterable
from typing import Protocol, cast


class TransportProtocol(Protocol):
    def send_payload(self, payload: bytes) -> None:
        ...


class USBWritableDeviceProtocol(Protocol):
    def write(self, endpoint: int, payload: bytes) -> None:
        ...


class USBConfigurableDeviceProtocol(USBWritableDeviceProtocol, Protocol):
    def set_configuration(self) -> None:
        ...


class USBTransportError(RuntimeError):
    pass


class USBTransport:
    def __init__(
        self,
        *,
        vendor_id: int,
        product_id: int,
        out_endpoint: int,
        device: USBWritableDeviceProtocol | None = None,
    ):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.out_endpoint = out_endpoint
        self._device = device

    def connect(self) -> USBWritableDeviceProtocol:
        if self._device is not None:
            return self._device

        try:
            import usb.core
        except ImportError as exc:
            raise USBTransportError("pyusb is required to talk to the DNAfx device") from exc

        try:
            device = cast(
                USBConfigurableDeviceProtocol | None,
                usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id),
            )
        except usb.core.NoBackendError as exc:
            raise USBTransportError(self._missing_backend_message()) from exc

        if device is None:
            raise USBTransportError(self._not_found_message(usb.core))

        try:
            is_kernel_driver_active = getattr(device, "is_kernel_driver_active", None)
            if callable(is_kernel_driver_active) and is_kernel_driver_active(0):
                detach_kernel_driver = getattr(device, "detach_kernel_driver", None)
                if callable(detach_kernel_driver):
                    detach_kernel_driver(0)
        except Exception:
            # Not all backends expose kernel driver control; failure here is safe to ignore
            pass

        try:
            device.set_configuration()
        except Exception as exc:
            raise USBTransportError(self._usb_error_message("configure", exc)) from exc

        self._device = device
        return device

    def send_payload(self, payload: bytes) -> None:
        device = self.connect()
        for _ in range(2):
            device = self._write_with_recovery(device, payload)

    def _write_with_recovery(self, device: USBWritableDeviceProtocol, payload: bytes) -> USBWritableDeviceProtocol:
        try:
            device.write(self.out_endpoint, payload)
            return device
        except Exception as exc:
            if not self._is_pipe_error(exc):
                raise USBTransportError(self._usb_error_message("write", exc)) from exc

        recovered_device = self._recover_from_pipe_error(device)
        try:
            recovered_device.write(self.out_endpoint, payload)
            return recovered_device
        except Exception as retry_exc:
            raise USBTransportError(self._usb_error_message("write", retry_exc)) from retry_exc

    def _recover_from_pipe_error(self, device: USBWritableDeviceProtocol) -> USBWritableDeviceProtocol:
        clear_halt = getattr(device, "clear_halt", None)
        if callable(clear_halt):
            try:
                clear_halt(self.out_endpoint)
                return device
            except Exception:
                pass

        self._device = None
        return self.connect()

    @staticmethod
    def _is_pipe_error(exc: Exception) -> bool:
        error_text = str(exc)
        errno = getattr(exc, "errno", None)
        return errno == 32 or "Pipe error" in error_text

    @staticmethod
    def _missing_backend_message() -> str:
        if sys.platform == "darwin":
            return (
                "No USB backend available. Install libusb on macOS with 'brew install libusb', "
                "then rerun the command."
            )

        return (
            "No USB backend available for pyusb. Install libusb for your platform and rerun the command."
        )

    def _not_found_message(self, usb_core: object) -> str:
        configured_device = f"{self.vendor_id:#06x}:{self.product_id:#06x}"
        visible_devices = self._visible_device_ids(usb_core)
        visible_text = "pyusb could not enumerate visible USB devices."
        if visible_devices:
            visible_text = f"pyusb currently sees: {', '.join(visible_devices)}."

        return (
            f"DNAfx device {configured_device} was not found. {visible_text} "
            "Check DNAFX_VENDOR_ID and DNAFX_PRODUCT_ID, confirm the DNAfx is connected over USB, "
            "and rerun the command."
        )

    @staticmethod
    def _visible_device_ids(usb_core: object) -> list[str]:
        find = getattr(usb_core, "find", None)
        if not callable(find):
            return []

        try:
            devices = cast(Iterable[object] | None, find(find_all=True))
        except Exception:
            return []

        if devices is None:
            return []

        visible_ids: list[str] = []
        for device in devices:
            vendor_id = getattr(device, "idVendor", None)
            product_id = getattr(device, "idProduct", None)
            if not isinstance(vendor_id, int) or not isinstance(product_id, int):
                continue

            visible_ids.append(f"{vendor_id:04x}:{product_id:04x}")

        return visible_ids

    @staticmethod
    def _usb_error_message(action: str, exc: Exception) -> str:
        error_text = str(exc)
        errno = getattr(exc, "errno", None)

        if errno == 13 or "Access denied" in error_text:
            if sys.platform == "darwin":
                return (
                    "Access denied while trying to claim the DNAfx USB interface. "
                    "On macOS, rerun the command with sudo, for example: "
                    "sudo dnafx-preset --transport usb --vendor-id 0483 --product-id 5703 --out-endpoint 02 set 1"
                )
            return (
                "Access denied while trying to claim the DNAfx USB interface. "
                "Rerun the command with the permissions required for raw USB access."
            )

        if errno == 19 or "No such device" in error_text:
            return "The DNAfx device disappeared during USB setup. Unplug and reconnect it, then rerun the command."

        if errno == 32 or "Pipe error" in error_text:
            return (
                "The DNAfx USB endpoint stalled while sending the preset command. "
                "The app retried once, but the device still rejected the write. "
                "Unplug and reconnect the DNAfx device, then rerun the command."
            )

        return f"Unable to {action} the DNAfx USB device: {error_text}"