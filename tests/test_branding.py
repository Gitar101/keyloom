"""Branding checks do not require a desktop session or keyboard hardware."""

from unittest.mock import Mock
from xml.etree import ElementTree

from PIL import Image
import pytest

from screensync import branding
from tools.build_branding import ASSETS, ICO_SIZES, PALETTE, PIXELS, PNG_SIZES, build_assets, pixel_image


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    folder = tmp_path_factory.mktemp("branding")
    build_assets(folder)
    return folder


def test_pixel_grid_has_transparency_and_only_brand_colors():
    assert len(PIXELS) == 16
    assert all(len(row) == 16 for row in PIXELS)
    image = pixel_image()
    expected = {tuple(bytes.fromhex(color[1:])) + (255,) for color in PALETTE.values()}
    assert set(image.get_flattened_data()) == expected | {(0, 0, 0, 0)}
    assert image.getbbox() == (2, 2, 14, 14)


@pytest.mark.parametrize("size", PNG_SIZES)
def test_pngs_are_exact_nearest_neighbor_art(generated, size):
    with Image.open(generated / f"keyloom-{size}.png") as image:
        assert image.size == (size, size)
        assert image.mode == "RGBA"
        assert image.tobytes() == pixel_image().resize(image.size, Image.Resampling.NEAREST).tobytes()
        assert not image.info


@pytest.mark.parametrize("name,sizes", [("keyloom.ico", ICO_SIZES), ("favicon.ico", (16, 32, 48))])
def test_ico_contains_unblurred_sizes(generated, name, sizes):
    with Image.open(generated / name) as image:
        assert image.ico.sizes() == {(size, size) for size in sizes}
        for size in sizes:
            frame = image.ico.getimage((size, size))
            expected = pixel_image().resize((size, size), Image.Resampling.NEAREST)
            assert frame.convert("RGBA").tobytes() == expected.tobytes()


def test_svg_is_accessible_self_contained_and_pixel_aligned(generated):
    root = ElementTree.fromstring((generated / "keyloom.svg").read_text(encoding="utf-8"))
    assert root.attrib["viewBox"] == "0 0 16 16"
    assert root.attrib["shape-rendering"] == "crispEdges"
    assert root.attrib["aria-labelledby"] == "title desc"
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    assert root.find("svg:title", namespace).text == "Keyloom"
    assert len(root.findall("svg:path", namespace)) == len(PALETTE)
    assert root.find("svg:image", namespace) is None


def test_checked_in_art_matches_generator(generated):
    for path in generated.iterdir():
        assert (ASSETS / path.name).read_bytes() == path.read_bytes(), path.name


def test_native_icon_application_retains_images_and_default(monkeypatch):
    root = Mock()
    photo = Mock(side_effect=lambda **kwargs: object())
    monkeypatch.setattr(branding.tk, "PhotoImage", photo)
    images = branding.apply_window_icon(root)
    root.iconbitmap.assert_called_once_with(default=str(branding.ASSETS / "keyloom.ico"))
    root.iconphoto.assert_called_once_with(True, *images)
    assert len(images) == 3
    assert [call.kwargs["master"] for call in photo.call_args_list] == [root] * 3
    assert [call.kwargs["file"] for call in photo.call_args_list] == [
        str(branding.ASSETS / f"keyloom-{size}.png") for size in branding.WINDOW_ICON_SIZES]
