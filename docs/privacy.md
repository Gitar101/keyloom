# Privacy and publication boundaries

Keyloom has no cloud backend, telemetry, account, update downloader, or screenshot-upload feature. The normal capture path keeps pixel data in memory and reduces it to 68 regional RGB values. It does not hook or log keystrokes. Device selection enumerates HID metadata only to select the exact supported vendor collection.

Errors are logged locally under `%LOCALAPPDATA%/Keyloom/`, with two rotated backups and a 200 KB rotation threshold. Tracebacks can contain paths from the machine that runs the app. Logs are not automatically shared. No screenshots or device serial numbers are deliberately logged.

Diagnostics run only when explicitly requested:

- `--smoke-test FILE` runs a short preview and saves RGB/timing JSON to FILE.
- `tools/verify_ui.py` saves a capture of the app window and a JSON result. The preview can reflect colors from the current desktop.
- `tools/verify_live.py` sends real keyboard lighting for a bounded test and writes color/timing JSON.

These outputs are ignored by Git. Review and redact anything you decide to share. A filename, error traceback, or screen preview can reveal information even when it is not a credential.

The public source and release are built from an explicit export of application files. Local recordings, screenshots, logs, raw reverse-engineering evidence, assistant memory/configuration, authentication files, virtual environments, and generated test results are not publication inputs. Dependency license notices are included, not development-environment metadata. This is publication hygiene, not a claim of a comprehensive third-party security audit.
