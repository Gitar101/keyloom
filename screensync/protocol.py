"""The allowlisted, non-profile-writing portion of the observed Apex100 protocol.

See docs/protocol.md for artifact addresses and remaining validation limits.
"""

from .colors import RGB

REPORT_SIZE = 64
REPORT_ID = 0x06
CHUNK_SIZE = 56
BASIC_INFO_SIZE = 57
READ_BASIC = 0x12
READ_FACTORY = 0x16
STREAM_RGB = 0x1D
MAX_LEDS = 512 // 3  # Vendor serializer's fixed RGB staging buffer.


class ProtocolError(RuntimeError):
    pass


def _packet(command: int, offset: int, length: int, payload: bytes = b"") -> bytes:
    if command not in (READ_BASIC, READ_FACTORY, STREAM_RGB):
        raise ValueError("Only basic-info/factory-matrix reads and streamed RGB are allowed")
    if not 0 <= offset <= 0xFFFF or not 1 <= length <= CHUNK_SIZE:
        raise ValueError("Invalid packet range")
    if command == STREAM_RGB and len(payload) != length:
        raise ValueError("RGB payload length mismatch")
    if command != STREAM_RGB and payload:
        raise ValueError("A read query must not contain a payload")
    packet = bytearray(REPORT_SIZE)
    packet[0:5] = bytes((REPORT_ID, command, offset & 255, offset >> 8, length))
    packet[8:8 + len(payload)] = payload
    # Checksum covers the whole report excluding the report ID. Both checksum
    # bytes and the final short chunk's unused tail start at zero every time.
    checksum = sum(packet[1:])
    packet[5:7] = checksum.to_bytes(2, "little")
    return bytes(packet)


def basic_info_packets() -> tuple[bytes, bytes]:
    return (_packet(READ_BASIC, 0, CHUNK_SIZE), _packet(READ_BASIC, CHUNK_SIZE, 1))


def factory_matrix_packets(led_count: int) -> tuple[bytes, ...]:
    if not 1 <= led_count <= MAX_LEDS:
        raise ValueError("Unsupported LED count")
    length = led_count * 3
    return tuple(_packet(READ_FACTORY, offset, min(CHUNK_SIZE, length - offset))
                 for offset in range(0, length, CHUNK_SIZE))


def uniform_packets(color: RGB, led_count: int) -> tuple[bytes, ...]:
    if not 1 <= led_count <= MAX_LEDS:
        raise ValueError("Device returned an unsupported LED count")
    if len(color) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in color):
        raise ValueError("RGB channels must be integers between 0 and 255")
    # Every physical LED receives the same RGB, so no logical key map is needed.
    # Chunk boundaries can split a three-byte RGB; offsets are byte offsets.
    return color_packets((color,) * led_count)


def color_packets(colors: tuple[RGB, ...]) -> tuple[bytes, ...]:
    if not 1 <= len(colors) <= MAX_LEDS:
        raise ValueError("Unsupported color frame size")
    if any(len(c) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in c) for c in colors):
        raise ValueError("Invalid per-key RGB data")
    payload = bytes(v for color in colors for v in color)
    return tuple(_packet(STREAM_RGB, offset, len(payload[offset:offset + CHUNK_SIZE]),
                         payload[offset:offset + CHUNK_SIZE])
                 for offset in range(0, len(payload), CHUNK_SIZE))


def validate_response(response: bytes, command: int) -> bytes:
    if len(response) != REPORT_SIZE:
        raise ProtocolError("Keyboard response timed out or was incomplete. Close other RGB apps and retry.")
    if response[0] != REPORT_ID or response[1] != command:
        raise ProtocolError("Unexpected keyboard response. Another app may be using the device.")
    if response[7] in (0x0F, 0xFE):
        raise ProtocolError(f"Keyboard rejected lighting transaction (status {response[7]:02X}).")
    return response


def parse_led_count(info: bytes) -> int:
    if len(info) != BASIC_INFO_SIZE:
        raise ProtocolError("Invalid keyboard basic-info response")
    count = info[4]
    if not 1 <= count <= MAX_LEDS:
        raise ProtocolError(f"Unsupported keyboard LED count: {count}. No lighting data sent.")
    return count
