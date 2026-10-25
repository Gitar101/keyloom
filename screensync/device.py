"""Exact-match HID transport, bounded reads, and streaming RGB only."""

import threading
import time

import hid

from .layout import Frame, parse_factory_mapping, physical_frame
from .protocol import (REPORT_SIZE, READ_BASIC, READ_FACTORY, STREAM_RGB, basic_info_packets,
                       factory_matrix_packets, color_packets, validate_response, parse_led_count)
from .windows import check_vendor_closed, report_sizes

VID = 0x28E9
PID = 0x31A3
USAGE_PAGE = 0xFF87
USAGE = 0x20
INTERFACE = 1


def select_device(devices: list[dict]) -> dict:
    matches = [d for d in devices
               if (d.get("vendor_id"), d.get("product_id"), d.get("usage_page"),
                   d.get("usage"), d.get("interface_number"))
               == (VID, PID, USAGE_PAGE, USAGE, INTERFACE)]
    if len(matches) != 1:
        raise RuntimeError("Connect exactly one Apex100 over its USB cable, then retry. "
                           "Wireless and other keyboards are not supported.")
    return matches[0]


class SyncStopped(Exception):
    """Cooperative cancellation, not a USB error."""


class Keyboard:
    def __init__(self, stop: threading.Event):
        self.stop = stop
        self.handle = None
        self.led_count = 0
        self.mapping = ()
        self.next_process_check = 0.0

    def __enter__(self):
        check_vendor_closed()
        self.next_process_check = time.monotonic() + 1
        device = select_device(hid.enumerate(VID, PID))
        if report_sizes(device["path"]) != (REPORT_SIZE, REPORT_SIZE):
            raise RuntimeError("Unexpected keyboard HID report sizes. No device reports sent.")
        self.handle = hid.device()
        try:
            self.handle.open_path(device["path"])
            self.handle.set_nonblocking(False)
            info = bytearray()
            for packet in basic_info_packets():
                response = self.exchange(packet, READ_BASIC)
                info.extend(response[8:8 + packet[4]])
            self.led_count = parse_led_count(bytes(info))
            matrix = bytearray()
            for packet in factory_matrix_packets(self.led_count):
                response = self.exchange(packet, READ_FACTORY)
                matrix.extend(response[8:8 + packet[4]])
            self.mapping = parse_factory_mapping(bytes(matrix), self.led_count)
        except Exception:
            self.close()
            raise
        return self

    def exchange(self, packet: bytes, command: int) -> bytes:
        if self.stop.is_set():
            raise SyncStopped()
        if len(packet) != REPORT_SIZE or packet[1] != command or command not in (READ_BASIC, READ_FACTORY, STREAM_RGB):
            raise ValueError("Refusing an unsupported keyboard command")
        if self.handle.write(packet) != REPORT_SIZE:
            raise RuntimeError("Keyboard write failed. Check the USB cable and close other RGB apps.")
        # Do not retry a timed-out chunk: late replies could be mistaken for
        # the next chunk's acknowledgement. Abort this session instead.
        response = bytes(self.handle.read(REPORT_SIZE, 150))
        return validate_response(response, command)

    def send(self, frame: Frame):
        now = time.monotonic()
        if now >= self.next_process_check:
            check_vendor_closed()
            self.next_process_check = time.monotonic() + 1
        # Even an unchanged picture must be streamed continuously. Suppressing
        # static frames lets firmware resume its onboard effect between updates.
        output = physical_frame(frame, self.mapping, self.led_count)
        for packet in color_packets(output):
            self.exchange(packet, STREAM_RGB)

    def close(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None

    def __exit__(self, *_):
        self.close()
