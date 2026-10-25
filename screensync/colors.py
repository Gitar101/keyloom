"""Color math, independent of screen capture and USB."""

import math

RGB = tuple[int, int, int]


def black_to_off(color: RGB, cutoff: int = 16) -> RGB:
    """Treat a near-black region as fully off, without shifting brighter hues."""
    if type(cutoff) is not int or not 0 <= cutoff <= 64:
        raise ValueError("Black cutoff must be an integer between 0 and 64")
    return (0, 0, 0) if max(color) <= cutoff else color


def fade_step(current: tuple[float, float, float], target: RGB,
              elapsed: float, transition_ms: float) -> tuple[float, float, float]:
    """Reach 99% of a fixed target in transition_ms, independent of frame rate.

    An exponential filter also stays continuous when the target changes before
    the previous transition finishes. Keep floats until the final USB encoding.
    """
    if not all(math.isfinite(v) for v in (*current, *target, elapsed, transition_ms)):
        raise ValueError("Fade inputs must be finite")
    if elapsed < 0 or transition_ms <= 0:
        raise ValueError("Invalid fade timing")
    gain = -math.expm1(-math.log(100) * elapsed / (transition_ms / 1000))
    return tuple(c + (t - c) * gain for c, t in zip(current, target))


def output_rgb(color: tuple[float, float, float], brightness: float = 100) -> RGB:
    if not math.isfinite(brightness) or not 0 <= brightness <= 100:
        raise ValueError("Brightness must be between 0 and 100")
    return tuple(max(0, min(255, round(c * brightness / 100))) for c in color)


def hex_rgb(color: RGB) -> str:
    return "#{:02X}{:02X}{:02X}".format(*color)
