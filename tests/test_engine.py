import threading
import time

import pytest

from screensync.engine import SyncEngine, Settings
from screensync.layout import KEYS


class FakeSampler:
    def __init__(self):
        self.closed = False
        self.frames = threading.Event()

    def __enter__(self):
        return self

    def read(self):
        self.frames.set()
        return ((255, 255, 255),) * len(KEYS)

    def __exit__(self, *_):
        self.closed = True


def stop_and_join(engine):
    engine.stop()
    engine._thread.join(timeout=2)
    assert not engine.running


def test_preview_never_constructs_keyboard_and_can_restart():
    sampler = FakeSampler()

    def forbidden(*_):
        pytest.fail("Preview constructed a hardware transport")

    engine = SyncEngine(lambda: sampler, forbidden)
    engine.start(preview=True)
    assert sampler.frames.wait(1)
    with pytest.raises(RuntimeError):
        engine.start(preview=True)
    stop_and_join(engine)
    assert sampler.closed and not engine.snapshot().error
    sampler.frames.clear()
    engine.start(preview=True)
    assert sampler.frames.wait(1)
    stop_and_join(engine)


def test_worker_error_reaches_ui():
    def broken(*_):
        raise RuntimeError("Disconnected")

    engine = SyncEngine(keyboard_factory=broken)
    engine.start()
    engine._thread.join(timeout=2)
    assert engine.snapshot().error
    assert engine.snapshot().status == "Disconnected"


@pytest.mark.parametrize("settings", [(-1, 400), (101, 400), (100, 0), (100, 2001), (float('nan'), 400)])
def test_invalid_settings(settings):
    with pytest.raises(ValueError):
        Settings(*settings)


@pytest.mark.parametrize("disconnect", [False, True])
def test_hardware_worker_cleanup_with_fake_transport(disconnect):
    sampler = FakeSampler()
    closed = threading.Event()
    sent = []

    class FakeKeyboard:
        led_count = 132

        def __init__(self, stop):
            self.stop = stop

        def __enter__(self):
            return self

        def send(self, color):
            sent.append(color)
            if disconnect:
                raise OSError("USB disconnected")
            self.stop.set()

        def __exit__(self, *_):
            closed.set()

    engine = SyncEngine(lambda: sampler, FakeKeyboard)
    engine.start()
    engine._thread.join(timeout=2)
    assert not engine.running
    assert closed.is_set() and sampler.closed and sent
    assert engine.snapshot().error is disconnect


@pytest.mark.parametrize("cutoff", [-1, 65, 1.5, float("nan")])
def test_invalid_black_cutoff_settings(cutoff):
    with pytest.raises(ValueError):
        Settings(black_cutoff=cutoff)


def test_near_black_regions_send_zero_rgb():
    class DarkSampler(FakeSampler):
        def read(self):
            return ((12, 15, 10),) * len(KEYS)

    sent = []

    class FakeKeyboard:
        led_count = 128

        def __init__(self, stop):
            self.stop = stop

        def __enter__(self):
            return self

        def send(self, frame):
            sent.append(frame)
            self.stop.set()

        def __exit__(self, *_):
            pass

    engine = SyncEngine(DarkSampler, FakeKeyboard)
    engine.start()
    engine._thread.join(timeout=2)
    assert sent == [((0, 0, 0),) * len(KEYS)]
    assert not engine.snapshot().error
