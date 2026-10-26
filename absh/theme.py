# absh — Absolute Shell for Termux
# -----------------------------------------------------------------------------
# theme.py: named colour themes and the ANSI/prompt_toolkit plumbing around them.
#
# A theme is a flat mapping of *roles* (not raw positions) to colours. The
# prompt, highlighter and toolbar all reference roles, so restyling absh is a
# matter of swapping one dict. Colours are plain hex strings — prompt_toolkit
# turns them into its own style tokens, and util.hex_to_ansi degrades them to
# the 256-colour codes Termux falls back to on older devices.
# -----------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field

# Every role the rest of absh may paint with. A theme may omit a role; the
# missing ones fall back to FALLBACK so a half-finished theme still renders.
ROLES = {
    "prompt_char", "prompt_char_error", "dir", "git", "git_dirty", "exit_code",
    "duration", "time", "battery", "sep", "suggestion", "cmd", "cmd_unknown",
    "flag", "string", "comment", "operator", "path", "var", "builtin", "plain",
}

FALLBACK = "#808080"


@dataclass
class Theme:
    name: str
    description: str = ""
    colors: dict[str, str] = field(default_factory=dict)

    def color(self, role: str) -> str:
        return self.colors.get(role, FALLBACK)


def _t(name: str, description: str, **colors: str) -> Theme:
    return Theme(name=name, description=description, colors=colors)


# Roles are grouped by what they touch: prompt chrome (char, dir, git, timing),
# command syntax (cmd/flag/string/operator/var/path), and feedback (exit_code).
THEMES: dict[str, Theme] = {
    "aurora": _t(
        "aurora", "Default. Cool greens and cyans on a dark Termux background.",
        prompt_char="#50fa7b", prompt_char_error="#ff5555",
        dir="#8be9fd", git="#bd93f9", git_dirty="#ffb86c",
        exit_code="#ff5555", duration="#6272a4", time="#6272a4",
        battery="#50fa7b", sep="#44475a", suggestion="#6272a4",
        cmd="#50fa7b", cmd_unknown="#ff79c6", flag="#8be9fd",
        string="#f1fa8c", comment="#6272a4", operator="#ff79c6",
        path="#8be9fd", var="#ff79c6", builtin="#bd93f9", plain="#f8f8f2",
    ),
    "sunset": _t(
        "sunset", "Warm oranges and pinks, easy on the eyes at night.",
        prompt_char="#ffb86c", prompt_char_error="#ff5555",
        dir="#ff79c6", git="#f1fa8c", git_dirty="#ffb86c",
        exit_code="#ff5555", duration="#6272a4", time="#6272a4",
        battery="#50fa7b", sep="#44475a", suggestion="#6272a4",
        cmd="#ffb86c", cmd_unknown="#ff79c6", flag="#8be9fd",
        string="#f1fa8c", comment="#6272a4", operator="#ff79c6",
        path="#8be9fd", var="#ff79c6", builtin="#bd93f9", plain="#f8f8f2",
    ),
    "mono": _t(
        "mono", "Single accent, minimal colour. Good for screen recordings.",
        prompt_char="#f8f8f2", prompt_char_error="#ff5555",
        dir="#f8f8f2", git="#ababab", git_dirty="#ffb86c",
        exit_code="#ff5555", duration="#666666", time="#666666",
        battery="#f8f8f2", sep="#333333", suggestion="#666666",
        cmd="#f8f8f2", cmd_unknown="#ff79c6", flag="#ababab",
        string="#ababab", comment="#666666", operator="#ababab",
        path="#f8f8f2", var="#ababab", builtin="#ababab", plain="#f8f8f2",
    ),
    "matrix": _t(
        "matrix", "Classic phosphor green on black.",
        prompt_char="#00ff41", prompt_char_error="#ff0000",
        dir="#00cc33", git="#00ff41", git_dirty="#aaff00",
        exit_code="#ff0000", duration="#007722", time="#007722",
        battery="#00ff41", sep="#003311", suggestion="#007722",
        cmd="#00ff41", cmd_unknown="#aaff00", flag="#00cc33",
        string="#aaff00", comment="#007722", operator="#00ff41",
        path="#00cc33", var="#aaff00", builtin="#00ff41", plain="#00ff41",
    ),
}

DEFAULT_THEME = "aurora"


def get(name: str) -> Theme:
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def names() -> list[str]:
    return sorted(THEMES)


def to_prompt_toolkit(theme: Theme) -> dict[str, str]:
    """Render a Theme as prompt_toolkit style tokens.

    Keys here are bare role names: Style.from_dict adds the "class:" prefix
    itself, and its name regex rejects a literal colon. Fragments elsewhere in
    absh still reference "class:role"; prompt_toolkit joins the two.
    """
    return {role: f"fg:{theme.color(role)}" for role in ROLES}
