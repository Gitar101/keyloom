"""Small Windows-only safety checks; never terminate another process."""

import ctypes
from ctypes import wintypes
import os


def check_vendor_closed() -> None:
    if os.name != "nt":
        raise RuntimeError("This app supports Windows only.")
    # Starting tasklist once per second adds visible gaps to the RGB stream.
    # Toolhelp enumerates process names directly, with no child process or shell.
    class ProcessEntry(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD),
                    ("pid", wintypes.DWORD), ("heap", ctypes.c_size_t),
                    ("module", wintypes.DWORD), ("threads", wintypes.DWORD),
                    ("parent", wintypes.DWORD), ("priority", wintypes.LONG),
                    ("flags", wintypes.DWORD), ("name", wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    entry = ProcessEntry()
    entry.size = ctypes.sizeof(entry)
    try:
        found = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while found:
            if entry.name.casefold() == "apex100.exe":
                raise RuntimeError("Exit Apex100 from its system-tray menu, then press Start again. "
                                   "Closing its window may leave it running.")
            found = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES is normal completion.
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(snapshot)


def report_sizes(path: bytes) -> tuple[int, int]:
    """Read HID capabilities with a zero-access handle; sends no device report."""
    class HidCaps(ctypes.Structure):
        _fields_ = [("usage", wintypes.USHORT), ("usage_page", wintypes.USHORT),
                    ("input_size", wintypes.USHORT), ("output_size", wintypes.USHORT),
                    ("feature_size", wintypes.USHORT),
                    ("reserved", wintypes.USHORT * 17),
                    ("counts", wintypes.USHORT * 10)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    hid = ctypes.WinDLL("hid", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    hid.HidD_GetPreparsedData.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
    hid.HidD_GetPreparsedData.restype = wintypes.BOOLEAN
    hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
    hid.HidD_FreePreparsedData.restype = wintypes.BOOLEAN
    hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HidCaps)]
    hid.HidP_GetCaps.restype = wintypes.LONG
    handle = kernel.CreateFileW(path.decode("utf-8"), 0, 3, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    preparsed = ctypes.c_void_p()
    try:
        if not hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
            raise ctypes.WinError(ctypes.get_last_error())
        caps = HidCaps()
        if hid.HidP_GetCaps(preparsed, ctypes.byref(caps)) != 0x00110000:
            raise RuntimeError("Cannot read keyboard HID report sizes")
        return caps.input_size, caps.output_size
    finally:
        if preparsed.value:
            hid.HidD_FreePreparsedData(preparsed)
        kernel.CloseHandle(handle)


class SingleInstance:
    def __init__(self):
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.kernel.CreateMutexW(None, False, "Local\\Apex100ScreenSync")
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == 183:
            self.close()
            raise RuntimeError("Keyloom or an earlier Screen Sync version is already open. Check the taskbar.")

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
