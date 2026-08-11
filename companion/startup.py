import sys
from pathlib import Path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def set_startup(enabled: bool, value_name: str = "VALSHOP Companion") -> None:
    if sys.platform != "win32":
        raise RuntimeError("Automatic startup registration is only supported on Windows")
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            if getattr(sys, "frozen", False):
                command = f'"{sys.executable}" --minimized'
            else:
                command = f'"{sys.executable}" "{Path(__file__).with_name("launcher.py")}"'
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, value_name)
            except FileNotFoundError:
                pass
