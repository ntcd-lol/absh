# absh — Absolute Shell for Termux
# -----------------------------------------------------------------------------
# shell.py: the interactive loop — prompt, keybindings, and dispatch.
#
# This is the only module that knows about prompt_toolkit's PromptSession. It
# wires the pieces together (theme -> prompt -> lexer -> completer -> executor)
# and owns the REPL state: last exit code, frecency on cd, and the Ctrl+R
# history search. Keeping the state here means the other modules stay reusable
# from a script or a test without dragging in a terminal.
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style, merge_styles

from . import config as config_mod
from . import prompt as prompt_mod
from . import termux
from . import theme as theme_mod
from .completer import AbshCompleter
from .executor import Executor
from .highlighter import ShellLexer
from .history import Frecency, History, HISTORY_PATH


@dataclass
class State:
    """Mutable REPL state threaded through the keybindings and prompt."""
    exit_code: int = 0
    last_line: str = ""
    frecency: Frecency = field(default_factory=Frecency)
    history: History = field(default_factory=History)


class Shell:
    def __init__(self) -> None:
        self.config = config_mod.load()
        self.state = State()
        self.executor = Executor(self.config, on_long=self._notify_long)
        self.completer = AbshCompleter(self.config)
        self.theme = theme_mod.get(self.config.general.theme)
        self.session: PromptSession | None = None

    # -- prompt / style ---------------------------------------------------

    def _style(self) -> Style:
        base = Style.from_dict(theme_mod.to_prompt_toolkit(self.theme))
        return merge_styles([base])

    def _prompt_text(self):
        return prompt_mod.build(
            self.theme,
            exit_code=self.state.exit_code,
            show_battery=self.config.general.show_battery,
            show_time=self.config.general.show_time,
        )

    # -- keybindings ------------------------------------------------------

    def _bindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("c-r")
        def _(event):
            # Reverse search through history; prompt_toolkit's built-in is
            # wired to our FileHistory so it sees every past command.
            event.current_buffer.start_history_search()

        @kb.add("c-c")
        def _(event):
            event.current_buffer.abort()

        @kb.add("c-d")
        def _(event):
            if not event.current_buffer.text:
                raise EOFError
            event.current_buffer.delete()

        return kb

    # -- notifications ----------------------------------------------------

    def _notify_long(self, line: str, duration: float, tail=()) -> None:
        msg = f"{line} — {duration:.1f}s"
        # The streamed tail is the freshest signal that a backgroundable
        # command actually finished with something worth reading.
        if tail:
            last = tail[-1].strip()
            if last:
                msg += f" · {last[:60]}"
        termux.toast(msg)
        termux.vibrate(60)

    # -- builtins that need shell state ------------------------------------

    def _handle_special(self, line: str) -> bool:
        """Run absh-only commands. Return True if the line was consumed."""
        parts = line.split()
        if not parts:
            return False
        cmd, args = parts[0], parts[1:]

        if cmd == "theme":
            return self._cmd_theme(args)
        if cmd == "z":
            return self._cmd_z(args)
        if cmd == "alias":
            return self._cmd_alias(args)
        if cmd == "reload":
            self.config = config_mod.load()
            self.theme = theme_mod.get(self.config.general.theme)
            self.completer.config = self.config
            self.completer.invalidate()
            print("absh: config reloaded")
            return True
        if cmd == "help":
            self._cmd_help()
            return True
        return False

    def _cmd_help(self) -> None:
        print("absh builtins:")
        print("  theme [name|--list]  switch colour theme (saved)")
        print("  z [query]            jump to the frecent matching directory")
        print("  alias [name=value]   list, create, or --del an alias")
        print("  reload               re-read ~/.absh/config.toml")
        print("  exit                 leave the shell")
        print("Everything else runs in bash. Ctrl+R searches history, Ctrl+D exits.")

    def _cmd_theme(self, args: list[str]) -> bool:
        if not args or args[0] in ("--list", "-l"):
            for name in theme_mod.names():
                marker = "*" if name == self.theme.name else " "
                print(f" {marker} {name}")
            return True
        chosen = args[0]
        if chosen not in theme_mod.THEMES:
            print(f"theme: unknown '{chosen}'. Try: {', '.join(theme_mod.names())}")
            return True
        self.theme = theme_mod.get(chosen)
        self.config.general.theme = chosen
        config_mod.save(self.config)
        print(f"theme -> {chosen}")
        return True

    def _cmd_z(self, args: list[str]) -> bool:
        query = args[0] if args else ""
        ranked = self.state.frecency.ranked(query)
        if not ranked:
            print("z: no match")
            return True
        target = ranked[0][0]
        try:
            old = os.getcwd()
            os.chdir(target)
        except (OSError, FileNotFoundError) as exc:
            print(f"z: {exc}")
            return True
        self.executor.env["OLDPWD"] = old
        self.executor.env["PWD"] = os.getcwd()
        print(os.getcwd())
        return True

    def _cmd_alias(self, args: list[str]) -> bool:
        if not args:
            for k in sorted(self.config.aliases):
                print(f"alias {k}='{self.config.aliases[k]}'")
            return True
        if args[0] == "--del" and len(args) > 1:
            self.config.aliases.pop(args[1], None)
            config_mod.save(self.config)
            self.completer.invalidate()
            return True
        # `alias name=value` or `alias name value`
        blob = " ".join(args)
        if "=" in blob:
            name, _, value = blob.partition("=")
        elif len(args) >= 2:
            name, value = args[0], " ".join(args[1:])
        else:
            print("alias: usage: alias name=value")
            return True
        self.config.aliases[name.strip()] = value.strip()
        config_mod.save(self.config)
        self.completer.invalidate()
        return True

    # -- main loop --------------------------------------------------------

    def run(self) -> int:
        self.session = PromptSession(
            history=FileHistory(str(HISTORY_PATH)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.completer,
            lexer=ShellLexer(command_names=self.completer.commands),
            key_bindings=self._bindings(),
            style=self._style(),
            multiline=False,
            complete_while_typing=True,
            enable_history_search=True,
        )
        print("absh — Absolute Shell. Type 'theme' to restyle, Ctrl+R to search history.")

        while True:
            try:
                line = self.session.prompt(self._prompt_text)
            except KeyboardInterrupt:
                continue
            except EOFError:
                print()
                return 0

            line = line.strip()
            if not line:
                continue
            self.state.history.add(line)
            self.state.last_line = line

            if self._handle_special(line):
                continue

            expanded = self.executor.expand_aliases(line)
            # Track directory changes for `z` scoring after the fact.
            before = os.getcwd()
            result = self.executor.run(expanded)
            after = os.getcwd()
            if after != before:
                self.state.frecency.add(after)
            self.state.exit_code = result.code


def main() -> int:
    if not shutil.which("bash"):
        # Only a warning: a missing bash still leaves the builtins usable.
        print("absh: bash not found; external commands may fail", file=sys.stderr)
    return Shell().run()
