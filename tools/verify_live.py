"""Explicit hardware test: stream the live screen, then stop. Never a unit test."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from screensync.device import Keyboard
from screensync.engine import SyncEngine, Settings
from screensync.windows import SingleInstance


def main():
    parser = argparse.ArgumentParser(description="Send spatial RGB to the connected Apex100 for a bounded test")
    parser.add_argument("--seconds", type=float, default=5)
    parser.add_argument("--brightness", type=float, default=25)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 30:
        raise SystemExit("Test duration must be 1..30 seconds")
    instance = SingleInstance()
    timestamps = []
    transport_info = {}

    class MeasuredKeyboard(Keyboard):
        def __enter__(self):
            result = super().__enter__()
            transport_info.update(buffer_slots=self.led_count, mapped_keys=len(self.mapping),
                                  unique_offsets=len(set(self.mapping)))
            return result

        def send(self, frame):
            super().send(frame)
            timestamps.append(time.monotonic())

    engine = SyncEngine(keyboard_factory=MeasuredKeyboard)
    engine.configure(Settings(brightness=args.brightness))
    try:
        print("Streaming real per-key screen colors. This test changes keyboard lighting.")
        engine.start()
        time.sleep(args.seconds)
    finally:
        engine.stop()
        if engine._thread:
            engine._thread.join(timeout=6)
        instance.close()
    result = asdict(engine.snapshot())
    gaps = [b - a for a, b in zip(timestamps, timestamps[1:])]
    result.update(transport_info)
    result["acknowledged_frames"] = len(timestamps)
    result["max_frame_gap_ms"] = round(max(gaps, default=0) * 1000, 2)
    result["mean_frame_gap_ms"] = round(sum(gaps) / len(gaps) * 1000, 2) if gaps else 0
    result["hardware_writes"] = True
    result["visual_flicker_check"] = "Not verified by this timing test"
    Path("verification-live.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = {k: v for k, v in result.items() if k not in ("target", "output")}
    print(json.dumps(summary, indent=2))
    if engine.running or result["error"] or len(timestamps) < 10:
        raise SystemExit("Live transport validation failed. See verification-live.json")


if __name__ == "__main__":
    main()
