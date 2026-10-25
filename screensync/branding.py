"""Window icons use the same assets in source and the one-file bundle."""

from pathlib import Path
import tkinter as tk


ASSETS = Path(__file__).resolve().parent.parent / "assets"
WINDOW_ICON_SIZES = (16, 32, 256)


def apply_window_icon(root: tk.Tk) -> tuple[tk.PhotoImage, ...]:
    root.iconbitmap(default=str(ASSETS / "keyloom.ico"))
    images = tuple(tk.PhotoImage(master=root, file=str(ASSETS / f"keyloom-{size}.png"))
                   for size in WINDOW_ICON_SIZES)
    root.iconphoto(True, *images)
    return images
