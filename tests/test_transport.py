import unittest
from types import ModuleType
from unittest.mock import patch

from dnafx_preset.transport import USBTransport


class FakeUSBDevice:
    def __init__(self) -> None:
        self.writes: list[tuple[int, bytes]] = []

    def write(self, endpoint: int, payload: bytes) -> None:
        self.writes.append((endpoint, payload))


class FakeConfigurableDevice:
    def __init__(self) -> None:
        self.reset_called = False
        self.configuration_set = False

    def reset(self) -> None:
        self.reset_called = True

    def is_kernel_driver_active(self, _interface: int) -> bool:
        return False

    def set_configuration(self) -> None:
        self.configuration_set = True


class FakePermissionError(Exception):
    def __init__(self, message: str, errno: int = 13) -> None:
        super().__init__(message)
        self.errno = errno


class FakePipeError(Exception):
    def __init__(self, message: str = "[Errno 32] Pipe error", errno: int = 32) -> None:
        super().__init__(message)
        self.errno = errno


class FakeAccessDeniedDevice:
    def write(self, _endpoint: int, _payload: bytes) -> None:
        raise FakePermissionError("[Errno 13] Access denied (insufficient permissions)")


class FakePipeRecoveryDevice:
    def __init__(self) -> None:
        self.writes: list[tuple[int, bytes]] = []
        self.clear_halt_calls: list[int] = []
        self._write_attempts = 0

    def write(self, endpoint: int, payload: bytes) -> None:
        self._write_attempts += 1
        if self._write_attempts == 1:
            raise FakePipeError()
        self.writes.append((endpoint, payload))

    def clear_halt(self, endpoint: int) -> None:
        self.clear_halt_calls.append(endpoint)


class FakeVisibleDevice:
    def __init__(self, vendor_id: int, product_id: int) -> None:
        self.idVendor = vendor_id
        self.idProduct = product_id


class USBTransportTests(unittest.TestCase):
    def test_send_payload_writes_twice(self) -> None:
        device = FakeUSBDevice()
        transport = USBTransport(vendor_id=0x0483, product_id=0x5703, out_endpoint=0x02, device=device)

        transport.send_payload(b"\x08\xaa\x55")

        self.assertEqual(device.writes, [(0x02, b"\x08\xaa\x55"), (0x02, b"\x08\xaa\x55")])

    def test_no_backend_error_has_actionable_message(self) -> None:
        transport = USBTransport(vendor_id=0x0483, product_id=0x5703, out_endpoint=0x02)

        class FakeNoBackendError(Exception):
            pass

        class FakeUsbCore:
            NoBackendError = FakeNoBackendError

            @staticmethod
            def find(**_kwargs):
                raise FakeNoBackendError("No backend available")

        fake_usb = ModuleType("usb")
        fake_usb.core = FakeUsbCore

        with patch.dict("sys.modules", {"usb": fake_usb, "usb.core": FakeUsbCore}):
            with self.assertRaisesRegex(Exception, "Install libusb"):
                transport.connect()

    def test_connect_does_not_reset_device(self) -> None:
        transport = USBTransport(vendor_id=0x0483, product_id=0x5703, out_endpoint=0x02)
        device = FakeConfigurableDevice()

        class FakeUsbCore:
            class NoBackendError(Exception):
                pass

            @staticmethod
            def find(**_kwargs):
                return device

        fake_usb = ModuleType("usb")
        fake_usb.core = FakeUsbCore

        with patch.dict("sys.modules", {"usb": fake_usb, "usb.core": FakeUsbCore}):
            connected_device = transport.connect()

        self.assertIs(connected_device, device)
        self.assertFalse(device.reset_called)
        self.assertTrue(device.configuration_set)

    def test_access_denied_error_has_actionable_message(self) -> None:
        transport = USBTransport(vendor_id=0x0483, product_id=0x5703, out_endpoint=0x02, device=FakeAccessDeniedDevice())

        with self.assertRaisesRegex(Exception, "sudo dnafx-preset"):
            transport.send_payload(b"\x08\xaa\x55")

    def test_pipe_error_retries_after_clearing_halt(self) -> None:
        device = FakePipeRecoveryDevice()
        transport = USBTransport(vendor_id=0x0483, product_id=0x5703, out_endpoint=0x02, device=device)

        transport.send_payload(b"\x08\xaa\x55")

        self.assertEqual(device.clear_halt_calls, [0x02])
        self.assertEqual(device.writes, [(0x02, b"\x08\xaa\x55"), (0x02, b"\x08\xaa\x55")])

    def test_not_found_error_lists_visible_usb_devices(self) -> None:
        transport = USBTransport(vendor_id=0x0483, product_id=0x5703, out_endpoint=0x02)

        class FakeUsbCore:
            class NoBackendError(Exception):
                pass

            @staticmethod
            def find(**kwargs):
                if kwargs.get("find_all"):
                    return [FakeVisibleDevice(0x1234, 0x5678), FakeVisibleDevice(0x0483, 0x9999)]
                return None

        fake_usb = ModuleType("usb")
        fake_usb.core = FakeUsbCore

        with patch.dict("sys.modules", {"usb": fake_usb, "usb.core": FakeUsbCore}):
            with self.assertRaisesRegex(Exception, "1234:5678, 0483:9999"):
                transport.connect()

    def test_not_found_error_includes_devices_after_first_eight(self) -> None:
        transport = USBTransport(vendor_id=0x0483, product_id=0x5703, out_endpoint=0x02)

        late_device = FakeVisibleDevice(0x0483, 0x5703)
        visible_devices = [FakeVisibleDevice(0x1000 + index, 0x2000 + index) for index in range(8)] + [late_device]

        class FakeUsbCore:
            class NoBackendError(Exception):
                pass

            @staticmethod
            def find(**kwargs):
                if kwargs.get("find_all"):
                    return visible_devices
                return None

        fake_usb = ModuleType("usb")
        fake_usb.core = FakeUsbCore

        with patch.dict("sys.modules", {"usb": fake_usb, "usb.core": FakeUsbCore}):
            with self.assertRaisesRegex(Exception, "0483:5703"):
                transport.connect()


if __name__ == "__main__":
    unittest.main()