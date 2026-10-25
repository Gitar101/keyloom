"""Physical GZS68 layout plus native factory key signatures.

Geometry: vendor RGB-68K-Keyboard-GZS68.xml. Signatures: RgDeviceManage.dll
reference table at 0x10065160, used by ParseKeyPosition at 0x1002c6b0.
XML key-code attributes are NOT reliable (Caps, Insert, modifiers differ).
"""

from dataclasses import dataclass

from .colors import RGB


@dataclass(frozen=True)
class Key:
    logical_index: int
    name: str
    x: int
    y: int
    width: int
    signature: tuple[int, int, int]
    height: int = 46


def _k(index, name, x, y, width, code, modifier=0, kind=16):
    return Key(index, name, x, y, width, (kind, modifier, code))


KEYS = (
    _k(0, "Esc", 0, 0, 46, 41),
    _k(23, "1", 50, 0, 46, 30), _k(24, "2", 100, 0, 46, 31),
    _k(25, "3", 150, 0, 46, 32), _k(26, "4", 200, 0, 46, 33),
    _k(27, "5", 250, 0, 46, 34), _k(28, "6", 300, 0, 46, 35),
    _k(29, "7", 350, 0, 46, 36), _k(30, "8", 400, 0, 46, 37),
    _k(31, "9", 450, 0, 46, 38), _k(32, "0", 500, 0, 46, 39),
    _k(33, "-", 550, 0, 46, 45), _k(34, "=", 600, 0, 46, 46),
    _k(35, "Backspace", 650, 0, 78, 42), _k(36, "Insert", 732, 0, 46, 73),
    _k(44, "Tab", 0, 50, 65, 43), _k(45, "Q", 69, 50, 46, 20),
    _k(46, "W", 119, 50, 46, 26), _k(47, "E", 169, 50, 46, 8),
    _k(48, "R", 219, 50, 46, 21), _k(49, "T", 269, 50, 46, 23),
    _k(50, "Y", 319, 50, 46, 28), _k(51, "U", 369, 50, 46, 24),
    _k(52, "I", 419, 50, 46, 12), _k(53, "O", 469, 50, 46, 18),
    _k(54, "P", 519, 50, 46, 19), _k(55, "[", 569, 50, 46, 47),
    _k(56, "]", 619, 50, 46, 48), _k(57, "\\", 669, 50, 59, 49),
    _k(58, "Delete", 732, 50, 46, 76),
    _k(66, "Caps", 0, 100, 79, 57), _k(67, "A", 83, 100, 46, 4),
    _k(68, "S", 133, 100, 46, 22), _k(69, "D", 183, 100, 46, 7),
    _k(70, "F", 233, 100, 46, 9), _k(71, "G", 283, 100, 46, 10),
    _k(72, "H", 333, 100, 46, 11), _k(73, "J", 383, 100, 46, 13),
    _k(74, "K", 433, 100, 46, 14), _k(75, "L", 483, 100, 46, 15),
    _k(76, ";", 533, 100, 46, 51), _k(77, "'", 583, 100, 46, 52),
    _k(78, "Enter", 633, 100, 95, 40), _k(38, "PgUp", 732, 100, 46, 75),
    _k(88, "Shift", 0, 150, 102, 0, modifier=2),
    _k(89, "Z", 106, 150, 46, 29), _k(90, "X", 156, 150, 46, 27),
    _k(91, "C", 206, 150, 46, 6), _k(92, "V", 256, 150, 46, 25),
    _k(93, "B", 306, 150, 46, 5), _k(94, "N", 356, 150, 46, 17),
    _k(95, "M", 406, 150, 46, 16), _k(96, ",", 456, 150, 46, 54),
    _k(97, ".", 506, 150, 46, 55), _k(98, "/", 556, 150, 46, 56),
    _k(99, "Shift", 606, 150, 72, 0, modifier=32),
    _k(100, "Up", 682, 150, 46, 82), _k(60, "PgDn", 732, 150, 46, 78),
    _k(110, "Ctrl", 0, 200, 56, 0, modifier=1),
    _k(111, "Win", 60, 200, 56, 0, modifier=8),
    _k(112, "Alt", 120, 200, 56, 0, modifier=4),
    _k(113, "Space", 180, 200, 298, 44),
    _k(114, "Alt", 482, 200, 46, 0, modifier=64),
    _k(109, "Fn", 532, 200, 46, 0, modifier=1, kind=96),
    _k(117, "Ctrl", 582, 200, 46, 0, modifier=16),
    _k(118, "Left", 632, 200, 46, 80), _k(119, "Down", 682, 200, 46, 81),
    _k(120, "Right", 732, 200, 46, 79),
)

Frame = tuple[RGB, ...]  # One color per KEYS entry, never raw USB order.
BLACK_FRAME: Frame = ((0, 0, 0),) * len(KEYS)
LAYOUT_WIDTH = max(key.x + key.width for key in KEYS)
LAYOUT_HEIGHT = max(key.y + key.height for key in KEYS)


def zone_boxes(width: int, height: int) -> tuple[tuple[int, int, int, int], ...]:
    """Cover the screen with five staggered rows following physical key widths.

    Small gaps between keys are split at their midpoint, so no screen strips
    are dropped. A wide Space key samples a proportionally wide bottom region.
    """
    if width < 32 or height < 5:
        raise ValueError("Sampling image is too small")
    rows = sorted({key.y for key in KEYS})
    boxes = []
    for key in KEYS:
        row = rows.index(key.y)
        row_keys = sorted((k for k in KEYS if k.y == key.y), key=lambda k: k.x)
        col = row_keys.index(key)
        left = 0 if col == 0 else (row_keys[col - 1].x + row_keys[col - 1].width + key.x) / 2
        right = LAYOUT_WIDTH if col == len(row_keys) - 1 else (key.x + key.width + row_keys[col + 1].x) / 2
        top = 0 if row == 0 else (rows[row - 1] + key.height + key.y) / 2
        bottom = LAYOUT_HEIGHT if row == len(rows) - 1 else (key.y + key.height + rows[row + 1]) / 2
        boxes.append((round(left * width / LAYOUT_WIDTH), round(top * height / LAYOUT_HEIGHT),
                      round(right * width / LAYOUT_WIDTH), round(bottom * height / LAYOUT_HEIGHT)))
    return tuple(boxes)


def parse_factory_mapping(matrix: bytes, led_count: int) -> tuple[int, ...]:
    if len(matrix) != led_count * 3:
        raise ValueError("Incomplete factory key matrix")
    records = [tuple(matrix[i:i + 3]) for i in range(0, len(matrix), 3)]
    mapping = []
    for key in KEYS:
        matches = [i for i, record in enumerate(records) if record == key.signature]
        if len(matches) != 1:
            raise ValueError(f"Cannot uniquely map {key.name}. No RGB sent; this keyboard layout may differ.")
        mapping.append(matches[0])
    return tuple(mapping)


def physical_frame(frame: Frame, mapping: tuple[int, ...], led_count: int) -> Frame:
    if len(frame) != len(KEYS) or len(mapping) != len(KEYS):
        raise ValueError("Incomplete per-key color frame")
    output = [(0, 0, 0)] * led_count
    for color, index in zip(frame, mapping):
        if not 0 <= index < led_count:
            raise ValueError("LED mapping outside device buffer")
        output[index] = color
    return tuple(output)
