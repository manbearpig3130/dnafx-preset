import pytest

from dnafx_preset.protocol import PACKET_SIZE, build_message, crc16_gsm, preset_change_message


def test_crc16_gsm_check_value() -> None:
    # The CRC catalogue's check value for CRC-16/GSM
    assert crc16_gsm(b"123456789") == 0xCE3C


@pytest.mark.parametrize(
    ("slot_number", "crc"),
    [(1, b"\xb0\xfb"), (51, b"\xa6\xea"), (59, b"\x27\xe2"), (96, b"\xcc\x7c"), (128, b"\x31\x52"), (200, b"\xf8\x9e")],
)
def test_preset_change_message(slot_number: int, crc: bytes) -> None:
    message = preset_change_message(slot_number)

    assert message[:9] == b"\x08\xaa\x55\x02\x00\x96" + bytes([slot_number]) + crc
    assert message[9:] == bytes(PACKET_SIZE - 9)


@pytest.mark.parametrize("slot_number", [0, 201])
def test_preset_change_message_rejects_slots_out_of_range(slot_number: int) -> None:
    with pytest.raises(IndexError, match="between 1 and 200"):
        preset_change_message(slot_number)


def test_build_message_matches_the_editors_greeting() -> None:
    # The official editor's first request (lminiero/dnafx-editor src/usb.c)
    assert build_message(0x00, b"\x00")[:9] == bytes.fromhex("08aa55020000001297")


def test_build_message_rejects_messages_longer_than_a_packet() -> None:
    with pytest.raises(ValueError, match="64-byte packet"):
        build_message(0x01, bytes(58))
