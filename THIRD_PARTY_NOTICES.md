# Third-party notices

Keyloom's original code uses the MIT license. Bundled dependencies retain their own licenses and copyright notices.

| Component | License / source |
| --- | --- |
| Python | [Python Software Foundation license](https://docs.python.org/3/license.html) |
| Tcl/Tk | [Tcl/Tk license terms](https://www.tcl-lang.org/software/tcltk/license.html) |
| MSS | [MIT](https://github.com/BoboTiG/python-mss) |
| Pillow and its bundled components | [MIT-CMU and included third-party notices](https://github.com/python-pillow/Pillow/blob/main/LICENSE) |
| Python hidapi bindings and HIDAPI | [License options and notices](https://github.com/trezor/cython-hidapi); [HIDAPI](https://github.com/libusb/hidapi) |
| PyInstaller bootloader | [GPL with distribution exception](https://pyinstaller.org/en/stable/license.html) |

`tools/collect_licenses.py` collects the installed distributions' license files, Python's license, and available Tcl/Tk notices into `third_party_licenses/`. The build embeds those files, this notice, and Keyloom's license in the executable. Runtime extraction uses PyInstaller's normal temporary directory.

Pytest and the other development/build tools are not part of Keyloom's runtime API. Their own licenses apply to their distributions. Ant Esports product names are used only to identify compatibility; the project includes no vendor application binaries or firmware.

The repository's blog cover includes an edited, user-supplied Ant Esports
keyboard product photograph and a Keyloom UI screenshot. The photograph and
manufacturer marks retain their owners' rights and are not covered by the
MIT code license. See `docs/assets/README.md`. Blog artwork is not bundled
into the executable. The original Keyloom pixel icon is MIT licensed.
