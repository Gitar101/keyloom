"""Single-worker lifecycle; no Tk calls outside the UI thread."""

from contextlib import nullcontext
from dataclasses import dataclass, replace
import logging
import threading
import time

from .capture import ScreenSampler
from .colors import fade_step, output_rgb, black_to_off
from .device import Keyboard, SyncStopped
from .layout import Frame, BLACK_FRAME, KEYS


@dataclass(frozen=True)
class Settings:
    brightness: float = 100
    transition_ms: float = 400
    black_cutoff: int = 16

    def __post_init__(self):
        if not 0 <= self.brightness <= 100 or not 100 <= self.transition_ms <= 2000:
            raise ValueError("Invalid brightness or transition time")
        if type(self.black_cutoff) is not int or not 0 <= self.black_cutoff <= 64:
            raise ValueError("Black cutoff must be an integer between 0 and 64")


@dataclass(frozen=True)
class State:
    status: str = "Ready. Each key follows its own region of your primary screen."
    target: Frame = BLACK_FRAME
    output: Frame = BLACK_FRAME
    fps: float = 0
    frames: int = 0
    led_count: int = 0
    error: bool = False


class SyncEngine:
    def __init__(self, sampler_factory=ScreenSampler, keyboard_factory=Keyboard):
        self._sampler_factory = sampler_factory
        self._keyboard_factory = keyboard_factory
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._settings = Settings()
        self._state = State()
        self._thread = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def stopping(self) -> bool:
        return self._stop.is_set() and self.running

    def snapshot(self) -> State:
        with self._lock:
            return self._state

    def configure(self, settings: Settings):
        with self._lock:
            self._settings = settings

    def _update(self, **kwargs):
        with self._lock:
            self._state = replace(self._state, **kwargs)

    def start(self, preview: bool = False):
        if self.running:
            raise RuntimeError("Sync is already running")
        self._stop.clear()
        self._update(status="Starting preview..." if preview else "Checking keyboard...",
                     error=False, frames=0, fps=0, led_count=0)
        self._thread = threading.Thread(target=self._run, args=(preview,),
                                        name="ScreenSync", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self, preview: bool):
        try:
            keyboard_context = nullcontext(None) if preview else self._keyboard_factory(self._stop)
            with keyboard_context as keyboard, self._sampler_factory() as sampler:
                self._update(status="Preview only. Keyboard is not being changed." if preview
                             else "Syncing 68 screen regions to their matching keys.",
                             led_count=0 if keyboard is None else keyboard.led_count)
                # Smooth both screen changes and brightness-slider changes.
                current = tuple(tuple(float(c) for c in color) for color in self.snapshot().output)
                previous = time.monotonic()
                stats_started = previous
                fps = 0.0
                stats_frames = 0
                total_frames = 0
                while not self._stop.is_set():
                    frame_started = time.monotonic()
                    target = sampler.read()
                    if len(target) != len(KEYS):
                        raise ValueError("Screen sampler returned an incomplete key grid")
                    now = time.monotonic()
                    with self._lock:
                        settings = self._settings
                    scaled_target = tuple(output_rgb(black_to_off(color, settings.black_cutoff),
                                                     settings.brightness) for color in target)
                    current = tuple(fade_step(color, goal, now - previous, settings.transition_ms)
                                    for color, goal in zip(current, scaled_target))
                    previous = now
                    output = tuple(output_rgb(color) for color in current)
                    if keyboard is not None:
                        keyboard.send(output)
                    stats_frames += 1
                    total_frames += 1
                    now = time.monotonic()
                    if now - stats_started >= 0.5:
                        fps = stats_frames / (now - stats_started)
                        stats_frames = 0
                        stats_started = now
                    self._update(target=target, output=output, frames=total_frames, fps=fps)
                    # No catch-up queue: USB latency lowers FPS instead of
                    # accumulating stale colors behind the current screen.
                    self._stop.wait(max(0, 0.05 - (time.monotonic() - frame_started)))
            self._update(status="Stopped. Keyboard streaming is off.", fps=0)
        except SyncStopped:
            self._update(status="Stopped.", fps=0)
        except Exception as error:
            logging.exception("Screen sync stopped")
            self._update(status=str(error) or type(error).__name__, error=True, fps=0)
