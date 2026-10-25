import math

from PIL import Image
import pytest

from screensync.capture import average_image, primary_monitor
from screensync.colors import fade_step, output_rgb, black_to_off


@pytest.mark.parametrize("color", [(0, 0, 0), (255, 255, 255), (255, 0, 0), (20, 100, 210)])
def test_solid_screen_average(color):
    assert average_image(Image.new("RGB", (200, 100), color)) == color


def test_balanced_screen_average():
    image = Image.new("RGB", (128, 72), "red")
    image.paste(Image.new("RGB", (64, 72), "blue"), (64, 0))
    assert average_image(image) == (128, 0, 128)


def test_white_fades_instead_of_jumping():
    partial = fade_step((0, 0, 0), (255, 255, 255), 0.05, 400)
    assert 0 < partial[0] < 255
    assert partial[0] == partial[1] == partial[2]
    assert output_rgb(fade_step((0, 0, 0), (255, 255, 255), 0.4, 400)) == (252, 252, 252)


def test_fade_is_frame_rate_independent():
    current = (0.0, 0.0, 0.0)
    for _ in range(8):
        current = fade_step(current, (255, 100, 20), 0.05, 400)
    assert current == pytest.approx(fade_step((0, 0, 0), (255, 100, 20), 0.4, 400))


def test_retarget_and_black_have_no_overshoot():
    color = fade_step((200, 50, 0), (0, 255, 10), 0.05, 400)
    assert 0 < color[0] < 200 and 50 < color[1] < 255 and 0 < color[2] < 10
    for _ in range(30):
        color = fade_step(color, (0, 0, 0), 0.05, 400)
    assert output_rgb(color) == (0, 0, 0)


def test_brightness_and_white_endpoints():
    assert output_rgb((255, 255, 255)) == (255, 255, 255)
    assert output_rgb((255, 100, 10), 0) == (0, 0, 0)
    assert output_rgb((200, 100, 20), 50) == (100, 50, 10)


@pytest.mark.parametrize("elapsed,duration", [(-1, 400), (0.1, 0), (math.nan, 400), (1, math.inf)])
def test_bad_fade_timing_rejected(elapsed, duration):
    with pytest.raises(ValueError):
        fade_step((0, 0, 0), (255, 255, 255), elapsed, duration)


def test_primary_is_not_assumed_to_be_monitor_one():
    monitors = [{}, {"left": 2560, "top": 100}, {"left": 0, "top": 0, "is_primary": True}]
    assert primary_monitor(monitors) is monitors[2]
    with pytest.raises(RuntimeError):
        primary_monitor([{}])


@pytest.mark.parametrize("color", [(0, 0, 0), (1, 2, 3), (16, 16, 16), (0, 16, 8)])
def test_near_black_regions_are_fully_off(color):
    assert black_to_off(color) == (0, 0, 0)


@pytest.mark.parametrize("color", [(17, 16, 16), (0, 0, 255), (255, 255, 255)])
def test_black_cutoff_preserves_brighter_regions(color):
    assert black_to_off(color) == color


def test_black_cutoff_is_adjustable_and_fades_to_zero():
    assert black_to_off((8, 8, 8), 0) == (8, 8, 8)
    assert black_to_off((32, 24, 16), 32) == (0, 0, 0)
    current = (255.0, 100.0, 50.0)
    for _ in range(30):
        current = fade_step(current, black_to_off((12, 15, 10)), 0.05, 400)
    assert output_rgb(current) == (0, 0, 0)


@pytest.mark.parametrize("cutoff", [-1, 65, 1.5, float("nan")])
def test_invalid_black_cutoff_is_rejected(cutoff):
    with pytest.raises(ValueError):
        black_to_off((0, 0, 0), cutoff)
