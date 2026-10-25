"""Local preview-only UI check. Saves only this app's own window for review."""

import ctypes
from dataclasses import asdict
import json
from pathlib import Path
import sys
import tkinter as tk

from PIL import ImageGrab

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from screensync.ui import App

ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
root = tk.Tk()
app = App(root)
app.preview_only.set(True)
root.after(100, app.start)


def finish():
    result = asdict(app.engine.snapshot())
    result["preview_only"] = True
    result["window_size"] = [root.winfo_width(), root.winfo_height()]
    x, y = root.winfo_rootx(), root.winfo_rooty()
    # This is an explicit app-UI test capture, not part of screen sampling.
    ImageGrab.grab(bbox=(x, y, x + root.winfo_width(), y + root.winfo_height())).save("verification-ui.png")
    Path("verification-ui.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    app.close()


root.after(3100, finish)
root.mainloop()
