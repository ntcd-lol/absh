# absh — Absolute Shell for Termux
# -----------------------------------------------------------------------------
# config.py: ~/.absh/config.toml — defaults, load, save.
#
# Reading uses stdlib tomllib; writing is a tiny hand-rolled emitter because the
# shape is fixed (two tables + an alias map) and pulling in a TOML writer for
# that would be overkill. Keys and alias values go through json.dumps, which is
# a valid TOML basic string for everything users actually type (aliases like
# ".." need quoting anyway).
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".absh"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_ALIASES = {
    "l": "ls",
    "ll": "ls -la",
    "la": "ls -A",
    "..": "cd ..",
    "...": "cd ../..",
    "c": "clear",
    "grep": "grep --color=auto",
    "df": "df -h",
    "du": "du -h",
    "update": "pkg update && pkg upgrade -y",
    "inst": "pkg install",
    "rmv": "pkg remove",
    "psr": "pkg search",
    "myip": "curl -s ifconfig.me",
}


@dataclass
class General:
    theme: str = "aurora"
    notify_after: float = 8.0
    show_battery: bool = True
    show_time: bool = False
    stream_output: bool = True


@dataclass
class UI:
    toolbar: bool = True
    autosuggest: bool = True
    highlight: bool = True


@dataclass
class Config:
    general: General = field(default_factory=General)
    ui: UI = field(default_factory=UI)
    aliases: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ALIASES))


def load() -> Config:
    """Read config.toml, writing it with defaults on first run."""
    cfg = Config()
    if CONFIG_PATH.is_file():
        try:
            data = tomllib.loads(CONFIG_PATH.read_text())
        except (OSError, tomllib.TOMLDecodeError) as exc:
            print(f"absh: ignoring broken config ({exc})")
            return cfg
        _merge(cfg, data)
    else:
        save(cfg)
    return cfg


def save(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(_dump(cfg))


def _merge(cfg: Config, data: dict) -> None:
    gen = data.get("general", {})
    for key in ("theme", "notify_after", "show_battery", "show_time", "stream_output"):
        if key in gen:
            setattr(cfg.general, key, gen[key])
    ui = data.get("ui", {})
    for key in ("toolbar", "autosuggest", "highlight"):
        if key in ui:
            setattr(cfg.ui, key, ui[key])
    if isinstance(data.get("aliases"), dict):
        cfg.aliases.update({str(k): str(v) for k, v in data["aliases"].items()})


def _dump(cfg: Config) -> str:
    out = ["[general]"]
    out.append(f"theme = {json.dumps(cfg.general.theme)}")
    out.append(f"notify_after = {cfg.general.notify_after}")
    out.append(f"show_battery = {'true' if cfg.general.show_battery else 'false'}")
    out.append(f"show_time = {'true' if cfg.general.show_time else 'false'}")
    out.append(f"stream_output = {'true' if cfg.general.stream_output else 'false'}")
    out += ["", "[ui]"]
    out.append(f"toolbar = {'true' if cfg.ui.toolbar else 'false'}")
    out.append(f"autosuggest = {'true' if cfg.ui.autosuggest else 'false'}")
    out.append(f"highlight = {'true' if cfg.ui.highlight else 'false'}")
    out += ["", "[aliases]"]
    for k, v in cfg.aliases.items():
        out.append(f"{json.dumps(k)} = {json.dumps(v)}")
    return "\n".join(out) + "\n"
