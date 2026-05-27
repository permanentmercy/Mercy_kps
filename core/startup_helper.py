import os
import sys
import ctypes
from ctypes import wintypes

# Win32 structures for Toolhelp32
LF_FACESIZE = 32
MAX_PATH = 260

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('cntUsage', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD),
        ('th32DefaultHeapID', ctypes.POINTER(wintypes.ULONG)),
        ('th32ModuleID', wintypes.DWORD),
        ('cntThreads', wintypes.DWORD),
        ('th32ParentProcessID', wintypes.DWORD),
        ('pcPriClassBase', wintypes.LONG),
        ('dwFlags', wintypes.DWORD),
        ('szExeFile', wintypes.WCHAR * MAX_PATH)
    ]

def is_process_running(process_name: str) -> bool:
    """Check if process is running by its executable name (e.g. 'osu!.exe')."""
    if not process_name:
        return False
        
    TH32CS_SNAPPROCESS = 0x00000002
    CreateToolhelp32Snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot
    Process32FirstW = ctypes.windll.kernel32.Process32FirstW
    Process32NextW = ctypes.windll.kernel32.Process32NextW
    CloseHandle = ctypes.windll.kernel32.CloseHandle

    hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if hProcessSnap == -1:
        return False

    pe32 = PROCESSENTRY32W()
    pe32.dwSize = ctypes.sizeof(PROCESSENTRY32W)

    target_name = process_name.lower()
    
    if not Process32FirstW(hProcessSnap, ctypes.byref(pe32)):
        CloseHandle(hProcessSnap)
        return False

    running = False
    while True:
        exe_name = pe32.szExeFile.lower()
        if target_name in exe_name:
            running = True
            break
        if not Process32NextW(hProcessSnap, ctypes.byref(pe32)):
            break

    CloseHandle(hProcessSnap)
    return running

def set_windows_startup(enabled: bool, silent: bool = False):
    """Register or unregister this program in HKEY_CURRENT_USER Run registry path."""
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "MercyKPS"
    
    exe_path = os.path.abspath(sys.executable)
    args = " --silent" if silent else ""
    if exe_path.endswith("python.exe") or exe_path.endswith("pythonw.exe"):
        # Running in development mode from python interpreter, run main.py
        main_py = os.path.abspath(sys.argv[0])
        cmd = f'"{exe_path}" "{main_py}"{args}'
    else:
        # Running as compiled standalone executable (PyInstaller)
        cmd = f'"{exe_path}"{args}'
        
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Failed to set startup registry: {e}")
