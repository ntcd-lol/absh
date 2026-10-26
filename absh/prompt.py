# absh — Absolute Shell for Termux
# -----------------------------------------------------------------------------
# prompt.py: build the two-line prompt.
#
# Layout is intentionally two lines: the top line is status (dir, git, battery,
# time, exit code) that a phone user glances at, the bottom is the caret where
# typing happens. Prompt_toolkit needs formatted-text fragments — tuples of
# (style_class, text) — which is why every helper returns a list of those
# rather than a coloured string.
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
from datetime import datetime

from . import termux
from .theme import Theme
from .util import git_info, shorten_path

# Segments are assembled left-to-right on line one. Keeping them as small
# functions means a theme can drop any of them without breaking the rest.


def _cwd_segment(theme: Theme) -> list[tuple[str, str]]:
    return [("class:dir", shorten_path(os.getcwd()))]


def _git_segment(theme: Theme) -> list[tuple[str, str]]:
    branch, dirty = git_info(os.getcwd())
    if not branch:
        return []
    style = "class:git_dirty" if dirty else "class:git"
    star = " *" if dirty else ""
    return [("class:sep", "  "), (style, f"{branch}{star}")]


def _battery_segment(theme: Theme) -> list[tuple[str, str]]:
    info = termux.battery()
    if not info or "capacity" not in info:
        return []
    level = info["capacity"]
    # Below 20% flip to the error colour so a dying phone is impossible to miss.
    style = "class:exit_code" if level < 20 else "class:battery"
    return [("class:sep", "  "), (style, f"{level}%")]


def _time_segment(theme: Theme) -> list[tuple[str, str]]:
    return [("class:sep", "  "), ("class:time", datetime.now().strftime("%H:%M"))]


def _exit_segment(theme: Theme, code: int) -> list[tuple[str, str]]:
    if code == 0:
        return []
    return [("class:sep", "  "), ("class:exit_code", f"✗ {code}")]


def build(theme: Theme, exit_code: int = 0, show_battery: bool = True,
          show_time: bool = True) -> list[tuple[str, str]]:
    """Return the formatted prompt: status line, newline, then the caret."""
    top: list[tuple[str, str]] = []
    top += _cwd_segment(theme)
    top += _git_segment(theme)
    if show_battery:
        top += _battery_segment(theme)
    if show_time:
        top += _time_segment(theme)
    top += _exit_segment(theme, exit_code)

    caret_style = "class:prompt_char_error" if exit_code != 0 else "class:prompt_char"
    top += [("\n", "\n"), (caret_style, "❯ ")]
    return top
