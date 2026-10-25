import pytest

from screensync.protocol import (basic_info_packets, uniform_packets, validate_response,
                                 parse_led_count, ProtocolError, READ_BASIC, STREAM_RGB)


def check_packet(packet, command):
    assert len(packet) == 64
    assert packet[0] == 6 and packet[1] == command and packet[7] == 0
    without_checksum = bytearray(packet)
    without_checksum[5:7] = b"\0\0"
    assert int.from_bytes(packet[5:7], "little") == sum(without_checksum[1:])


def test_basic_queries_cover_57_bytes():
    first, last = basic_info_packets()
    check_packet(first, READ_BASIC)
    check_packet(last, READ_BASIC)
    assert first[2:5] == bytes((0, 0, 56))
    assert last[2:5] == bytes((56, 0, 1))
    assert not any(first[8:]) and not any(last[8:])


@pytest.mark.parametrize("leds", [1, 18, 19, 68, 100, 132, 170])
@pytest.mark.parametrize("color", [(255, 255, 255), (0, 0, 0), (3, 17, 241)])
def test_packet_reassembly_and_checksum(leds, color):
    payload = bytearray()
    for packet in uniform_packets(color, leds):
        check_packet(packet, STREAM_RGB)
        assert int.from_bytes(packet[2:4], "little") == len(payload)
        length = packet[4]
        assert 1 <= length <= 56
        payload.extend(packet[8:8 + length])
        assert not any(packet[8 + length:])
    assert payload == bytes(color) * leds


@pytest.mark.parametrize("count", [0, 171, 255])
def test_unsafe_led_counts_rejected(count):
    with pytest.raises(ValueError):
        uniform_packets((0, 0, 0), count)
    info = bytearray(57)
    info[4] = count
    with pytest.raises(ProtocolError):
        parse_led_count(bytes(info))


def test_parse_led_count():
    info = bytearray(57)
    info[4] = 132
    assert parse_led_count(bytes(info)) == 132


@pytest.mark.parametrize("response", [b"", bytes(63), bytes(64), bytes([6, 0x12]) + bytes(62),
                                     bytes([6, 0x1D]) + bytes(5) + b"\x0f" + bytes(56),
                                     bytes([6, 0x1D]) + bytes(5) + b"\xfe" + bytes(56)])
def test_bad_acknowledgements_rejected(response):
    with pytest.raises(ProtocolError):
        validate_response(response, STREAM_RGB)


def test_good_acknowledgement():
    response = bytes([6, 0x1D]) + bytes(62)
    assert validate_response(response, STREAM_RGB) == response
