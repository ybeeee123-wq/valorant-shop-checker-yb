import multiprocessing
import os
import sys

import keyring

from callback import LocalCallback
from credentials import SERVICE
from desktop import run_desktop
from startup import RUN_KEY, set_startup


def packaged_smoke_preflight() -> None:
    """Exercise packaged-only integrations without touching user credentials."""
    callback = LocalCallback()
    callback.start()
    callback.stop()
    probe_name = "packaged_smoke_probe"
    probe_names = [probe_name, f"{probe_name}.0", f"{probe_name}.1"]
    try:
        for index, name in enumerate(probe_names):
            value = "ok" if index == 0 else str(index) * 900
            keyring.set_password(SERVICE, name, value)
            if keyring.get_password(SERVICE, name) != value:
                raise RuntimeError("Windows Credential Manager smoke test failed")
    finally:
        for name in probe_names:
            try:
                keyring.delete_password(SERVICE, name)
            except keyring.errors.PasswordDeleteError:
                pass
    if sys.platform == "win32":
        import winreg

        startup_probe = "VALSHOP Packaged Smoke Probe"
        try:
            set_startup(True, startup_probe)
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                command, _kind = winreg.QueryValueEx(key, startup_probe)
            if sys.executable.lower() not in command.lower():
                raise RuntimeError("Windows startup command does not use the packaged executable")
        finally:
            set_startup(False, startup_probe)


def main() -> None:
    multiprocessing.freeze_support()
    smoke_mode = os.environ.get("VALSHOP_SMOKE_TEST")
    if smoke_mode == "1":
        packaged_smoke_preflight()
    if smoke_mode:
        return
    raise SystemExit(run_desktop())


if __name__ == "__main__":
    main()
