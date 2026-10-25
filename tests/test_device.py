import threading

import pytest

from screensync import device
from screensync.device import Keyboard, select_device, SyncStopped
from screensync.protocol import basic_info_packets, ProtocolError
from screensync.layout import KEYS


def matching_device():
    return dict(vendor_id=0x28E9, product_id=0x31A3, usage_page=0xFF87,
                usage=0x20, interface_number=1, path=b"verified-path")


def test_exact_selection_and_ambiguity():
    good = matching_device()
    keyboard = dict(good, usage_page=1, usage=6)
    other_vendor = dict(good, vendor_id=0x04D9)
    wrong_collection = dict(good, usage_page=0xFF88, usage=0x21)
    assert select_device([keyboard, other_vendor, wrong_collection, good]) is good
    for candidates in ([], [keyboard, other_vendor, wrong_collection], [good, good]):
        with pytest.raises(RuntimeError):
            select_device(candidates)


class FakeHid:
    def __init__(self, ack=True, count=132):
        self.sent = []
        self.closed = False
        self.ack = ack
        self.count = count

    def open_path(self, path):
        assert path == b"verified-path"

    def set_nonblocking(self, value):
        assert value is False

    def write(self, packet):
        self.sent.append(packet)
        return 64

    def read(self, length, timeout):
        assert length == 64 and 0 < timeout <= 150
        if not self.ack:
            return []
        response = bytearray(self.sent[-1])
        if response[1] == 0x12:
            info = bytearray(57)
            info[4] = self.count
            offset = int.from_bytes(response[2:4], "little")
            response[8:8 + response[4]] = info[offset:offset + response[4]]
        elif response[1] == 0x16:
            matrix = b"".join(bytes(key.signature) for key in KEYS) + bytes((self.count - len(KEYS)) * 3)
            offset = int.from_bytes(response[2:4], "little")
            response[8:8 + response[4]] = matrix[offset:offset + response[4]]
        return response

    def close(self):
        self.closed = True


def setup_fake(monkeypatch, fake):
    monkeypatch.setattr(device, "check_vendor_closed", lambda: None)
    monkeypatch.setattr(device, "report_sizes", lambda _: (64, 64))
    monkeypatch.setattr(device.hid, "enumerate", lambda *_: [matching_device()])
    monkeypatch.setattr(device.hid, "device", lambda: fake)


def test_initialization_continuous_static_frames_and_close(monkeypatch):
    fake = FakeHid()
    setup_fake(monkeypatch, fake)
    with Keyboard(threading.Event()) as keyboard:
        assert keyboard.led_count == 132
        frame = ((255, 255, 255),) * len(KEYS)
        keyboard.send(frame)
        sent_count = len(fake.sent)
        keyboard.send(frame)
        assert len(fake.sent) == sent_count + 8  # Never suppress an identical frame.
        assert {packet[1] for packet in fake.sent} == {0x12, 0x16, 0x1D}
        assert sent_count == 2 + 8 + 8
    assert fake.closed


def test_bad_info_closes_handle_and_sends_no_rgb(monkeypatch):
    fake = FakeHid(count=255)
    setup_fake(monkeypatch, fake)
    with pytest.raises(ProtocolError):
        with Keyboard(threading.Event()):
            pass
    assert fake.closed
    assert {p[1] for p in fake.sent} == {0x12}


def test_timeout_is_not_retried():
    keyboard = Keyboard(threading.Event())
    keyboard.handle = fake = FakeHid(ack=False)
    with pytest.raises(ProtocolError):
        keyboard.exchange(basic_info_packets()[0], 0x12)
    assert len(fake.sent) == 1


def test_stop_sends_nothing():
    stop = threading.Event()
    stop.set()
    keyboard = Keyboard(stop)
    keyboard.handle = fake = FakeHid()
    with pytest.raises(SyncStopped):
        keyboard.exchange(basic_info_packets()[0], 0x12)
    assert fake.sent == []


def test_vendor_app_blocks_before_open(monkeypatch):
    fake = FakeHid()
    setup_fake(monkeypatch, fake)

    def blocked():
        raise RuntimeError("Exit Apex100")

    monkeypatch.setattr(device, "check_vendor_closed", blocked)
    with pytest.raises(RuntimeError, match="Exit Apex100"):
        Keyboard(threading.Event()).__enter__()
    assert not fake.sent


def test_unexpected_report_sizes_block_before_open(monkeypatch):
    fake = FakeHid()
    setup_fake(monkeypatch, fake)
    monkeypatch.setattr(device, "report_sizes", lambda _: (65, 65))
    with pytest.raises(RuntimeError, match="report sizes"):
        Keyboard(threading.Event()).__enter__()
    assert not fake.sent
