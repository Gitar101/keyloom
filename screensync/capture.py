"""In-memory primary-monitor capture. No image persistence or network access."""

from PIL import Image, ImageStat
from mss import MSS

from .colors import RGB
from .layout import Frame, zone_boxes


def average_image(image: Image.Image) -> RGB:
    # BOX averages areas rather than selecting a few pixels. The small image
    # makes the statistics inexpensive while preserving white/black endpoints.
    reduced = image.convert("RGB").resize((64, 36), Image.Resampling.BOX)
    return tuple(round(channel) for channel in ImageStat.Stat(reduced).mean)


def primary_monitor(monitors: list[dict]) -> dict:
    physical = monitors[1:]  # Index zero is the whole virtual desktop.
    for monitor in physical:
        if monitor.get("is_primary") is True:
            return monitor
    for monitor in physical:
        if monitor["left"] == 0 and monitor["top"] == 0:
            return monitor
    raise RuntimeError("Primary display not found. Check Windows display settings.")


SAMPLE_SIZE = (320, 180)
SAMPLE_BOXES = zone_boxes(*SAMPLE_SIZE)


def sample_zones(image: Image.Image) -> Frame:
    """Area-average every physical key's screen region, without mixing zones."""
    reduced = image.resize(SAMPLE_SIZE, Image.Resampling.BOX)
    return tuple(tuple(round(v) for v in ImageStat.Stat(reduced.crop(box)).mean[:3])
                 for box in SAMPLE_BOXES)


class ScreenSampler:
    def __enter__(self):
        # MSS owns thread-local GDI resources: construct it in the worker.
        self.capture = MSS()
        try:
            self.monitor = primary_monitor(self.capture.monitors)
        except Exception:
            self.capture.close()
            raise
        return self

    def read(self) -> Frame:
        frame = self.capture.grab(self.monitor)
        image = Image.frombuffer("RGB", frame.size, frame.bgra, "raw", "BGRX")
        return sample_zones(image)

    def __exit__(self, *_):
        self.capture.close()
