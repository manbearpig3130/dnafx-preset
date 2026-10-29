import pytest

from dnafx_preset.hid_transport import HIDTransport, HIDTransportError


class FakeHIDDevice:
    def __init__(self, *, open_error: Exception | None = None, write_result: int | Exception | None = None) -> None:
        self.opened: tuple[int, int] | None = None
        self.writes: list[bytes] = []
        self.closed = False
        self._open_error = open_error
        self._write_result = write_result

    def open(self, vendor_id: int, product_id: int) -> None:
        if self._open_error is not None:
            raise self._open_error
        self.opened = (vendor_id, product_id)

    def write(self, buff: bytes) -> int:
        if isinstance(self._write_result, Exception):
            raise self._write_result
        self.writes.append(buff)
        return len(buff) if self._write_result is None else self._write_result

    def close(self) -> None:
        self.closed = True


def make_transport(device: FakeHIDDevice) -> HIDTransport:
    return HIDTransport(vendor_id=0x0483, product_id=0x5703, device_factory=lambda: device)


def test_send_payload_writes_one_padded_report_and_closes() -> None:
    device = FakeHIDDevice()

    make_transport(device).send_payload(b"\x08\xaa\x55")

    assert device.opened == (0x0483, 0x5703)
    assert device.writes == [b"\x00\x08\xaa\x55" + bytes(61)]
    assert device.closed is True


def test_opens_the_device_for_every_payload() -> None:
    devices = [FakeHIDDevice(), FakeHIDDevice()]
    transport = HIDTransport(vendor_id=0x0483, product_id=0x5703, device_factory=lambda: devices.pop(0))

    transport.send_payload(b"\x01")
    transport.send_payload(b"\x02")

    assert devices == []


def test_rejects_payloads_longer_than_a_report() -> None:
    device = FakeHIDDevice()

    with pytest.raises(HIDTransportError, match="at most 64"):
        make_transport(device).send_payload(bytes(65))

    assert device.opened is None


def test_open_failure_has_actionable_message() -> None:
    device = FakeHIDDevice(open_error=OSError("open failed"))

    with pytest.raises(HIDTransportError, match="USB-B"):
        make_transport(device).send_payload(b"\x08")


def test_write_error_closes_the_device() -> None:
    device = FakeHIDDevice(write_result=OSError("write error"))

    with pytest.raises(HIDTransportError, match="write error"):
        make_transport(device).send_payload(b"\x08")

    assert device.closed is True


def test_negative_write_result_is_an_error() -> None:
    device = FakeHIDDevice(write_result=-1)

    with pytest.raises(HIDTransportError, match="Unable to write"):
        make_transport(device).send_payload(b"\x08")

    assert device.closed is True
