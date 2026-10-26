# absh — Absolute Shell for Termux
# -----------------------------------------------------------------------------
# termux.py: thin wrappers over the termux-api CLIs, all optional.
#
# Every call is guarded: on a plain Linux box (or when the API is missing) the
# functions return None / do nothing, so nothing else in absh has to ask "am I
# on a phone?" before showing a battery level or firing a toast.
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time

_BATTERY_TTL = 30.0
_battery_cache: dict = {}


def _have(name: str) -> bool:
    return shutil.which(name) is not None


def is_termux() -> bool:
    return os.environ.get("PREFIX", "").startswith("/data/data/com.termux")


def battery() -> dict | None:
    """{capacity, plugged, status} or None if the API is not around."""
    now = time.time()
    if _battery_cache and now - _battery_cache["ts"] < _BATTERY_TTL:
        return _battery_cache["data"]
    data = None
    if _have("termux-battery-status"):
        try:
            out = subprocess.run(
                ["termux-battery-status"], capture_output=True, text=True, timeout=2
            )
            data = json.loads(out.stdout)
        except (OSError, ValueError, subprocess.SubprocessError):
            data = None
    _battery_cache.update(ts=now, data=data)
    return data


def _fire(args: list[str]) -> None:
    if not _have(args[0]):
        return
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def toast(msg: str, short: bool = True) -> None:
    args = ["termux-toast", "-s"] if short else ["termux-toast"]
    _fire(args + [msg])


def notify(title: str, msg: str) -> None:
    _fire(["termux-notification", "--title", title, "--content", msg])


def vibrate(ms: int = 40) -> None:
    _fire(["termux-vibrate", "-d", str(ms)])


def clipboard_get() -> str:
    if not _have("termux-clipboard-get"):
        return ""
    try:
        out = subprocess.run(
            ["termux-clipboard-get"], capture_output=True, text=True, timeout=2
        )
        return out.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def clipboard_set(text: str) -> None:
    if not _have("termux-clipboard-set"):
        return
    try:
        subprocess.run(["termux-clipboard-set"], input=text, text=True, timeout=2)
    except OSError:
        pass
