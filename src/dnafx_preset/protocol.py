from __future__ import annotations

# DNAfx GiT USB messages, as reverse engineered by lminiero/dnafx-editor (MIT).
# Every message is one 64-byte packet, zero padded:
#
#   [count] AA 55 [length, 2 bytes LE] [command] [data...] [CRC-16, 2 bytes BE]
#
# where length counts the command and data bytes, count is the number of bytes after
# itself, and the CRC covers the length, command and data bytes.

PACKET_SIZE = 64
SLOT_COUNT = 200
CHANGE_PRESET = 0x96


def crc16_gsm(data: bytes) -> int:
    # CRC-16/GSM: polynomial 0x1021, initial value 0, not reflected, output XOR 0xFFFF
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc ^ 0xFFFF


def build_message(command: int, data: bytes) -> bytes:
    body = (len(data) + 1).to_bytes(2, "little") + bytes([command]) + data
    crc = crc16_gsm(body)
    message = b"\xaa\x55" + body + crc.to_bytes(2, "big")
    if len(message) >= PACKET_SIZE:
        raise ValueError(f"Message does not fit in one {PACKET_SIZE}-byte packet")
    return (bytes([len(message)]) + message).ljust(PACKET_SIZE, b"\x00")


def preset_change_message(slot_number: int) -> bytes:
    if slot_number < 1 or slot_number > SLOT_COUNT:
        raise IndexError(f"Slot must be between 1 and {SLOT_COUNT}")
    return build_message(CHANGE_PRESET, bytes([slot_number]))
