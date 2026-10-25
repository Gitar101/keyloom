"""Generate all Keyloom icons from one transparent 16-pixel drawing."""

from pathlib import Path

from PIL import Image


PIXELS = (
    "................",
    "................",
    "...##########...",
    "...#CCCVVAAA#...",
    "...#CCCVVAAA#...",
    "...#CCCVVAAA#...",
    "...#CCCVVAAA#...",
    "...#CCCVVAAA#...",
    "...##########...",
    ".......##.......",
    ".....######.....",
    "..############..",
    "..#CCC#VV#AAA#..",
    "..############..",
    "................",
    "................",
)
PALETTE = {"#": "#142539", "C": "#39D6E7", "V": "#9A81F5", "A": "#FFBC62"}
PNG_SIZES = (16, 32, 256, 512)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
ASSETS = Path(__file__).resolve().parent.parent / "assets"


def pixel_image() -> Image.Image:
    image = Image.new("RGBA", (16, 16))
    for y, row in enumerate(PIXELS):
        for x, pixel in enumerate(row):
            if pixel != ".":
                image.putpixel((x, y), tuple(bytes.fromhex(PALETTE[pixel][1:])) + (255,))
    return image


def svg_text() -> str:
    # Merge horizontal pixel runs into one path per color. No raster references.
    paths = []
    for pixel, color in PALETTE.items():
        runs = []
        for y, row in enumerate(PIXELS):
            x = 0
            while x < len(row):
                if row[x] != pixel:
                    x += 1
                    continue
                end = x + 1
                while end < len(row) and row[end] == pixel:
                    end += 1
                runs.append(f"M{x} {y}h{end - x}v1H{x}z")
                x = end
        fill = "currentColor" if pixel == "#" else color
        paths.append(f'  <path fill="{fill}" d="{"".join(runs)}"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" '
            'shape-rendering="crispEdges" style="color:#142539" role="img" '
            'aria-labelledby="title desc">\n'
            '  <title id="title">Keyloom</title>\n'
            '  <desc id="desc">Pixel-art monitor and keyboard sharing cyan, '
            'violet, and amber screen regions.</desc>\n'
            + "\n".join(paths) + "\n</svg>\n")


def save_ico(path: Path, image: Image.Image, sizes: tuple[int, ...]) -> None:
    frames = [image.resize((size, size), Image.Resampling.NEAREST) for size in sizes]
    # Supply every size explicitly: ICO's automatic downsampling would blur pixels.
    frames[-1].save(path, format="ICO", sizes=[frame.size for frame in frames],
                    append_images=frames[:-1])


def build_assets(folder: Path = ASSETS) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    image = pixel_image()
    for size in PNG_SIZES:
        image.resize((size, size), Image.Resampling.NEAREST).save(folder / f"keyloom-{size}.png")
    save_ico(folder / "keyloom.ico", image, ICO_SIZES)
    save_ico(folder / "favicon.ico", image, (16, 32, 48))
    (folder / "keyloom.svg").write_text(svg_text(), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build_assets()
    print("Generated Keyloom SVG, PNG, Windows icon, and favicon.")
