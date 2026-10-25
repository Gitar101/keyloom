"""Native desktop controls. The worker never touches these Tk widgets."""

import argparse
from dataclasses import asdict
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from .branding import apply_window_icon
from .colors import hex_rgb
from .engine import SyncEngine, Settings
from .layout import KEYS, BLACK_FRAME, LAYOUT_WIDTH, LAYOUT_HEIGHT, zone_boxes
from .windows import SingleInstance

BG = "#EDF1F5"
PAPER = "#FFFFFF"
INK = "#142539"
MUTED = "#5B6D80"
BLUE = "#276AAF"
LINE = "#C9D4DF"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.engine = SyncEngine()
        self.closing = False
        root.title("Keyloom")
        self.icon_images = apply_window_icon(root)
        root.geometry("720x680")
        root.minsize(620, 660)
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=INK, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=("Segoe UI", 25, "bold"))
        style.configure("TCheckbutton", background=BG, foreground=INK, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("Horizontal.TScale", background=BG, troughcolor=LINE)
        style.configure("TButton", font=("Segoe UI", 11), padding=(18, 10))
        style.configure("Start.TButton", background=BLUE, foreground=PAPER, borderwidth=0)
        style.map("Start.TButton", background=[("active", "#205D9D"), ("disabled", LINE)],
                  foreground=[("disabled", MUTED)])

        content = ttk.Frame(root, padding=(30, 22))
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        ttk.Label(content, text="Keyloom", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(content, text="Screen regions mapped to individual keys. Smooth transitions.",
                  style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 14))

        self.preview_canvas = tk.Canvas(content, bg=PAPER, highlightthickness=1,
                                        highlightbackground=LINE, height=184)
        self.preview_canvas.grid(row=2, column=0, sticky="ew")
        self.preview_canvas.bind("<Configure>", self._draw_preview)
        self.colors = (BLACK_FRAME, BLACK_FRAME)

        self.brightness = tk.DoubleVar(value=100)
        self.transition = tk.DoubleVar(value=400)
        self.black_cutoff = tk.DoubleVar(value=16)
        self.brightness_text = tk.StringVar()
        self.transition_text = tk.StringVar()
        self.black_cutoff_text = tk.StringVar()
        self._slider(content, 3, "Brightness", self.brightness_text, self.brightness, 0, 100)
        self._slider(content, 5, "Transition time", self.transition_text, self.transition, 100, 2000)
        self._slider(content, 7, "Black cutoff", self.black_cutoff_text, self.black_cutoff, 0, 64)
        self._settings_changed()

        self.preview_only = tk.BooleanVar(value=False)
        self.preview_check = ttk.Checkbutton(content, text="Preview only (don't change keyboard)",
                                             variable=self.preview_only)
        self.preview_check.grid(row=9, column=0, sticky="w", pady=(7, 14))
        buttons = ttk.Frame(content)
        buttons.grid(row=10, column=0, sticky="ew")
        self.start_button = ttk.Button(buttons, text="Start sync", style="Start.TButton", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(buttons, text="Stop", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=(10, 0))
        self.metrics = ttk.Label(buttons, text="USB cable required", style="Muted.TLabel")
        self.metrics.pack(side="right")

        self.status = tk.StringVar(value=self.engine.snapshot().status)
        self.status_label = ttk.Label(content, textvariable=self.status, wraplength=640)
        self.status_label.grid(row=11, column=0, sticky="ew", pady=(14, 4))
        ttk.Label(content, text="Top-left screen region matches the top-left keys, and so on.\n"
                  "Exit Apex100 first. Capture stays local. Minimize for best results.",
                  style="Muted.TLabel").grid(row=12, column=0, sticky="w", pady=(4, 0))
        content.bind("<Configure>", lambda e: self.status_label.configure(wraplength=max(200, e.width - 60)))
        root.after(50, self._poll)

    def _slider(self, parent, row, title, text_var, variable, low, high):
        line = ttk.Frame(parent)
        line.grid(row=row, column=0, sticky="ew", pady=(13, 2))
        ttk.Label(line, text=title).pack(side="left")
        ttk.Label(line, textvariable=text_var, style="Muted.TLabel").pack(side="right")
        ttk.Scale(parent, from_=low, to=high, variable=variable, command=self._settings_changed).grid(
            row=row + 1, column=0, sticky="ew")

    def _settings_changed(self, *_):
        brightness = round(self.brightness.get())
        transition = round(self.transition.get() / 50) * 50
        self.brightness_text.set(f"{brightness}%")
        self.transition_text.set(f"{transition} ms")
        black_cutoff = round(self.black_cutoff.get())
        self.black_cutoff_text.set(f"{black_cutoff} / 255")
        self.engine.configure(Settings(brightness=brightness, transition_ms=transition,
                                       black_cutoff=black_cutoff))

    def _draw_preview(self, _event=None):
        canvas = self.preview_canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        center_left, center_right = width * 0.25, width * 0.75
        canvas.create_text(center_left, 21, text="Screen", fill=MUTED, font=("Segoe UI", 10))
        canvas.create_text(center_right, 21, text="Keyboard", fill=MUTED, font=("Segoe UI", 10))
        canvas.create_line(width / 2, 18, width / 2, 167, fill=LINE)
        screen_width = min(220, width * 0.39)
        screen_left = center_left - screen_width / 2
        for i, box in enumerate(zone_boxes(320, 180)):
            x0, y0, x1, y1 = box
            canvas.create_rectangle(screen_left + x0 * screen_width / 320, 45 + y0 * 76 / 180,
                                    screen_left + x1 * screen_width / 320, 45 + y1 * 76 / 180,
                                    fill=hex_rgb(self.colors[0][i]), outline=LINE, width=0.5,
                                    tags=f"screen_{i}")
        canvas.create_rectangle(screen_left, 45, screen_left + screen_width, 121,
                                outline=INK, width=2)
        canvas.create_line(center_left, 122, center_left, 130, fill=INK, width=3)
        canvas.create_line(center_left - 16, 131, center_left + 16, 131, fill=INK, width=3)
        key_scale = min(270, width * 0.43) / LAYOUT_WIDTH
        left = center_right - LAYOUT_WIDTH * key_scale / 2
        for i, key in enumerate(KEYS):
            x, y = left + key.x * key_scale, 47 + key.y * key_scale
            canvas.create_rectangle(x, y, x + key.width * key_scale, y + key.height * key_scale,
                                    fill=hex_rgb(self.colors[1][i]), outline=LINE, tags=f"key_{i}")
        canvas.create_text(center_left, 158, text="68 screen regions", fill=INK, font=("Segoe UI", 10))
        canvas.create_text(center_right, 158, text="68 independent fades", fill=INK, font=("Segoe UI", 10))

    def start(self):
        self.engine.start(preview=self.preview_only.get())
        self.start_button.configure(state="disabled")
        self.preview_check.configure(state="disabled")

    def stop(self):
        self.engine.stop()
        self.status.set("Stopping after the current transaction...")
        self.stop_button.configure(state="disabled")

    def _poll(self):
        state = self.engine.snapshot()
        running = self.engine.running
        if self.closing:
            if not running:
                self.root.destroy()
                return
            self.status.set("Stopping and closing the keyboard connection...")
        else:
            self.status.set("Stopping after the current transaction..." if self.engine.stopping else state.status)
            self.status_label.configure(foreground="#A32D34" if state.error else INK)
            self.start_button.configure(state="disabled" if running else "normal")
            self.stop_button.configure(state="normal" if running and not self.engine.stopping else "disabled")
            self.preview_check.configure(state="disabled" if running else "normal")
        self.colors = (state.target, state.output)
        for i, (target, output) in enumerate(zip(state.target, state.output)):
            self.preview_canvas.itemconfigure(f"screen_{i}", fill=hex_rgb(target))
            self.preview_canvas.itemconfigure(f"key_{i}", fill=hex_rgb(output))
        prefix = "Preview" if self.preview_only.get() else "68 keys" if state.led_count else "USB"
        self.metrics.configure(text=f"{prefix}  |  {state.fps:.0f} fps" if running else "USB cable required")
        self.root.after(50, self._poll)

    def close(self):
        self.closing = True
        self.engine.stop()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")


def setup_logging():
    folder = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Keyloom"
    folder.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(folder / "app.log", maxBytes=200_000, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler],
                        format="%(asctime)s %(levelname)s %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Smooth primary-screen color on the wired Apex100")
    parser.add_argument("--smoke-test", type=Path, help="Run a 3-second preview-only test and write JSON results")
    args = parser.parse_args()
    setup_logging()
    if sys.platform != "win32":
        raise SystemExit("This app requires Windows")
    import ctypes
    # Set DPI awareness before Tk or MSS creates any windows/resources.
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    root = tk.Tk()
    root.withdraw()
    instance = None
    try:
        instance = SingleInstance()
        app = App(root)
        root.deiconify()
        if args.smoke_test:
            app.preview_only.set(True)
            root.after(100, app.start)

            def finish_smoke():
                result = asdict(app.engine.snapshot())
                result["preview_only"] = True
                result["icon_sizes"] = [[image.width(), image.height()] for image in app.icon_images]
                args.smoke_test.write_text(json.dumps(result, indent=2), encoding="utf-8")
                app.close()

            root.after(3100, finish_smoke)
        root.mainloop()
    except Exception as error:
        logging.exception("App failed")
        messagebox.showerror("Keyloom", str(error), parent=root)
        root.destroy()
    finally:
        if instance is not None:
            instance.close()
