from PIL import Image
import pytest

from screensync.capture import sample_zones, SAMPLE_SIZE, SAMPLE_BOXES
from screensync.layout import KEYS, zone_boxes, parse_factory_mapping, physical_frame
from screensync.protocol import color_packets, factory_matrix_packets


def test_every_screen_pixel_belongs_to_exactly_one_key():
    width, height = SAMPLE_SIZE
    coverage = [0] * (width * height)
    for x0, y0, x1, y1 in SAMPLE_BOXES:
        assert x1 > x0 and y1 > y0
        for y in range(y0, y1):
            for x in range(x0, x1):
                coverage[y * width + x] += 1
    assert set(coverage) == {1}


def test_top_left_and_bottom_right_stay_spatially_separate():
    image = Image.new("RGB", SAMPLE_SIZE, (0, 0, 0))
    image.paste((255, 0, 0), SAMPLE_BOXES[0])
    image.paste((0, 0, 255), SAMPLE_BOXES[-1])
    colors = sample_zones(image)
    assert colors[0] == (255, 0, 0)
    assert colors[-1] == (0, 0, 255)
    assert all(color == (0, 0, 0) for color in colors[1:-1])


def test_each_region_preserves_its_own_average():
    image = Image.new("RGB", SAMPLE_SIZE)
    expected = tuple((i * 3, 255 - i * 3, i) for i in range(len(KEYS)))
    for box, color in zip(SAMPLE_BOXES, expected):
        image.paste(color, box)
    assert sample_zones(image) == expected


def test_wide_space_key_has_wide_screen_region():
    space = next(i for i, key in enumerate(KEYS) if key.name == "Space")
    left, _, right, _ = SAMPLE_BOXES[space]
    a, _, b, _ = SAMPLE_BOXES[space - 1]
    assert right - left > 4 * (b - a)


def test_factory_order_is_not_assumed_to_be_visual_order():
    records = [key.signature for key in reversed(KEYS)] + [(0, 0, 0)] * 60
    mapping = parse_factory_mapping(bytes(v for record in records for v in record), 128)
    assert mapping == tuple(reversed(range(len(KEYS))))
    logical_colors = tuple((i, 0, 0) for i in range(len(KEYS)))
    physical = physical_frame(logical_colors, mapping, 128)
    assert physical[0] == (67, 0, 0) and physical[67] == (0, 0, 0)
    assert physical[68:] == ((0, 0, 0),) * 60
    packets = color_packets(physical)
    reassembled = b"".join(packet[8:8 + packet[4]] for packet in packets)
    assert reassembled == bytes(v for color in physical for v in color)


def test_missing_or_duplicate_factory_key_is_rejected():
    records = [key.signature for key in KEYS]
    records[-1] = records[0]
    with pytest.raises(ValueError, match="uniquely"):
        parse_factory_mapping(bytes(v for record in records for v in record), len(records))


def test_factory_queries_are_read_only_and_cover_matrix():
    packets = factory_matrix_packets(128)
    assert len(packets) == 7
    assert sum(p[4] for p in packets) == 384
    assert all(p[1] == 0x16 and not any(p[8:]) for p in packets)
