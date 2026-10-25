# Testing

## Unit tests

```powershell
.venv/Scripts/python.exe -m pytest -q
```

The suite uses fake HID transports. It covers region averages and non-overlapping coverage, corner orientation, factory-order remapping, independent time-based fades, black cutoff and zero RGB, packet chunking/checksums, continuous static frames, device selection, errors, cancellation, and cleanup. It never writes to hardware.

Branding checks cover the transparent pixel palette, exact nearest-neighbor
PNG/ICO variants, self-contained accessible SVG, reproducibility of checked-in
assets, and native-window icon application using a fake Tk window.

## Packaged preview smoke test

Close other Keyloom/Screen Sync instances first:

```powershell
& './dist/Keyloom.exe' --smoke-test "$PWD/verification-packaged.json"
```

The app runs preview-only for about three seconds, writes local RGB/timing JSON, and closes. There should be 68 target and output colors, multiple frames, `error: false`, and `icon_sizes: [[16, 16], [32, 32], [256, 256]]`. This also verifies the packaged runtime can load its icons. No keyboard reports are sent.

## Explicit UI diagnostic

```powershell
.venv/Scripts/python.exe tools/verify_ui.py
```

This saves the app window to `verification-ui.png` and writes local JSON. Review the window for clipping and correct screen/key geometry. The image is a diagnostic output, not a repository asset.

## Explicit hardware diagnostic

Exit the vendor app and connect the supported keyboard over USB:

```powershell
.venv/Scripts/python.exe tools/verify_live.py --seconds 5 --brightness 25
```

This changes real lighting and writes `verification-live.json`. It verifies factory mapping and packet acknowledgements and measures frame gaps. It does not automatically prove visual smoothness or that an onboard effect never intervenes.

For a visual test, display red/green/blue regions in different screen corners and check the corresponding key positions. Display black in one region and verify its keys fade off. Keep the app minimized during comparison. Check both moving content and a static image. Stop if the device behaves unexpectedly; do not reset or flash it as part of testing.
