$ErrorActionPreference = 'Stop'
$Python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path $Python)) { throw 'Create .venv and install requirements-dev.txt first. See README.md.' }
Push-Location $PSScriptRoot
try {
    & $Python tools/build_branding.py
    if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed' }
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    & $Python tools/collect_licenses.py
    if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
    & $Python -m PyInstaller --noconfirm --clean --onefile --windowed --name 'Keyloom' --icon 'assets/keyloom.ico' --add-data 'assets/keyloom.ico:assets' --add-data 'assets/keyloom-16.png:assets' --add-data 'assets/keyloom-32.png:assets' --add-data 'assets/keyloom-256.png:assets' --add-data 'LICENSE:.' --add-data 'THIRD_PARTY_NOTICES.md:.' --add-data 'third_party_licenses:third_party_licenses' screen_sync.py
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
} finally {
    Pop-Location
}
