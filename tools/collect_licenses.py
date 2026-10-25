"""Collect installed dependency notices for bundling, not environment metadata."""

from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "third_party_licenses"
    output.mkdir(exist_ok=True)
    for package in ("mss", "Pillow", "hidapi", "pyinstaller"):
        dist = distribution(package)
        found = False
        for item in dist.files or ():
            relative = Path(str(item))
            if "licenses" not in relative.parts:
                continue
            source = Path(dist.locate_file(item))
            if not source.is_file():
                continue
            tail = Path(*relative.parts[relative.parts.index("licenses") + 1:])
            destination = output / package / tail
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            found = True
        if not found:
            raise RuntimeError(f"No installed license notices found for {package}")

    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise RuntimeError("Python's license file is missing")
    shutil.copyfile(python_license, output / "Python-LICENSE.txt")
    for license_file in (Path(sys.base_prefix) / "tcl").glob("*/license*"):
        if license_file.is_file():
            shutil.copyfile(license_file, output / f"{license_file.parent.name}-{license_file.name}")
    print("Collected third-party license notices")


if __name__ == "__main__":
    main()
