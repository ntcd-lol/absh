# absh — Absolute Shell for Termux
# -----------------------------------------------------------------------------
# executor.py: turn one input line into a running process.
#
# The model is deliberate: absh is a smart line editor on top of bash, not a
# bash clone. Stateful builtins a user expects to persist (cd, export, alias)
# are handled in-process; everything else goes to a real `bash -c` so pipes,
# globs and redirects behave exactly as bash does them. Reimplementing a shell
# grammar is a losing game — delegating keeps 100% compatibility for free.
#
# Execution has two modes. Plain mode hands the child the real terminal, which
# keeps full-screen programs and colours intact. Streaming mode (the default)
# pipes stdout back so output is shown live and its tail kept for the
# completion notification — a fair trade for the bulk of phone commands, with
# a small list of terminal-hungry programs routed around it.
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from collections import deque
from dataclasses import dataclass

from . import termux
from .config import Config

# Lines of output kept after a streamed command; feeds the long-run toast.
_TAIL_MAX = 200

# Best-effort list of programs that want a real terminal on stdout. Piping
# them would drop colours or break full-screen rendering, so they bypass the
# stream. Not exhaustive — `stream_output = false` is the reliable escape hatch.
_NEEDS_TTY = {
    "vim", "vi", "nvim", "emacs", "nano", "micro",
    "less", "more", "man", "most",
    "top", "htop", "btop", "glances", "watch",
    "ssh", "sudo", "su", "doas", "mosh",
    "tmux", "screen",
    "python", "python3", "ipython", "irb", "node", "deno",
    "mysql", "psql", "sqlite3", "redis-cli",
}


# The shell binary to delegate to. Termux ships bash at $PREFIX/bin/bash; the
# fallback to plain "sh" keeps absh usable on a stripped-down environment.
def _shell_binary() -> str:
    return os.environ.get("ABS_H_SHELL") or os.environ.get("SHELL") or "bash"


@dataclass
class Result:
    code: int
    duration: float
    builtin: bool = False
    tail: tuple[str, ...] = ()


class Executor:
    def __init__(self, config: Config, on_long=None) -> None:
        self.config = config
        # Callback fired when a command runs longer than notify_after; wired to
        # termux.toast by the shell so the executor stays importable headless.
        self.on_long = on_long
        self.env = os.environ.copy()

    def run(self, line: str, stdin=None, stdout=None) -> Result:
        line = line.strip()
        if not line:
            return Result(0, 0.0)

        start = time.time()
        # Builtins get first refusal; an unknown name falls through to bash so
        # aliases, functions and PATH lookups keep working untouched.
        builtin = self._try_builtin(line)
        if builtin is not None:
            return Result(builtin, time.time() - start, builtin=True)

        tail: tuple[str, ...] = ()
        if self._should_stream(line, stdout):
            code, tail_list = self._run_streaming(line, stdin=stdin)
            tail = tuple(tail_list)
        else:
            code = self._run_external(line, stdin=stdin, stdout=stdout)

        duration = time.time() - start
        self._maybe_notify(line, duration, tail)
        return Result(code, duration, tail=tail)

    # -- external ---------------------------------------------------------

    def _should_stream(self, line: str, stdout) -> bool:
        # Only pipe when we own the terminal and the program is not in the
        # TTY-hungry set; a caller-supplied stdout always gets plain mode.
        if stdout is not None:
            return False
        if not self.config.general.stream_output:
            return False
        return not self._needs_tty(line)

    @staticmethod
    def _needs_tty(line: str) -> bool:
        try:
            parts = shlex.split(line, posix=True)
        except ValueError:
            return False
        return bool(parts) and os.path.basename(parts[0]) in _NEEDS_TTY

    def _run_streaming(self, line: str, stdin=None) -> tuple[int, list[str]]:
        """Run the command, forwarding output live while keeping a tail."""
        tail: deque[str] = deque(maxlen=_TAIL_MAX)
        try:
            proc = subprocess.Popen(
                [_shell_binary(), "-c", line],
                env=self.env,
                stdin=stdin,          # None inherits the terminal for input
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # merge so errors land in the tail
                text=True,
                bufsize=1,            # line-buffered reads from the child
            )
        except FileNotFoundError:
            print(f"absh: shell not found: {_shell_binary()}", file=sys.stderr)
            return 127, []
        except KeyboardInterrupt:
            return 130, []

        assert proc.stdout is not None
        try:
            for chunk in proc.stdout:
                sys.stdout.write(chunk)
                sys.stdout.flush()
                tail.append(chunk.rstrip("\r\n"))
        except BrokenPipeError:
            proc.kill()
        except KeyboardInterrupt:
            proc.kill()
            proc.wait()
            return 130, list(tail)
        return proc.wait(), list(tail)

    def _run_external(self, line: str, stdin=None, stdout=None) -> int:
        try:
            proc = subprocess.run(
                [_shell_binary(), "-c", line],
                env=self.env,
                stdin=stdin if stdin is not None else sys.stdin,
                stdout=stdout if stdout is not None else None,
            )
            return proc.returncode
        except FileNotFoundError:
            print(f"absh: shell not found: {_shell_binary()}", file=sys.stderr)
            return 127
        except KeyboardInterrupt:
            # bash itself reports 130 on SIGINT; mirror that so `$?` reads right.
            return 130

    def _maybe_notify(self, line: str, duration: float, tail=()) -> None:
        threshold = self.config.general.notify_after
        if threshold and duration >= threshold and self.on_long:
            self.on_long(line, duration, tail)

    # -- builtins ---------------------------------------------------------

    def _try_builtin(self, line: str) -> int | None:
        parts = shlex.split(line, posix=True)
        if not parts:
            return None
        name, args = parts[0], parts[1:]

        if name in ("cd", "chdir"):
            return self._cd(args)
        if name == "export":
            return self._export(args)
        if name == "unset":
            for a in args:
                self.env.pop(a, None)
            return 0
        if name == "exit":
            code = int(args[0]) if args and args[0].isdigit() else 0
            raise SystemExit(code)
        return None

    def _cd(self, args: list[str]) -> int:
        target = os.path.expanduser(args[0]) if args else os.path.expanduser("~")
        # `cd -` swaps to OLDPWD like bash; the env var lives in self.env so it
        # survives across the bash subprocesses we spawn.
        if target == "-":
            target = self.env.get("OLDPWD") or os.getcwd()
        try:
            old = os.getcwd()
            os.chdir(target)
        except (FileNotFoundError, NotADirectoryError) as exc:
            print(f"cd: {exc}", file=sys.stderr)
            return 1
        except PermissionError:
            print(f"cd: permission denied: {target}", file=sys.stderr)
            return 1
        self.env["OLDPWD"] = old
        self.env["PWD"] = os.getcwd()
        return 0

    def _export(self, args: list[str]) -> int:
        if not args:
            for k in sorted(self.env):
                print(f"{k}={self.env[k]}")
            return 0
        for a in args:
            if "=" in a:
                key, _, value = a.partition("=")
                self.env[key] = value
        return 0

    # -- aliases ----------------------------------------------------------

    def expand_aliases(self, line: str) -> str:
        """Expand the first word through aliases, one level deep.

        One level only, with a visited-set guard, so a recursive alias cannot
        spin forever — the same rule bash applies.
        """
        parts = line.split(None, 1)
        if not parts:
            return line
        head, rest = parts[0], parts[1] if len(parts) > 1 else ""
        seen: set[str] = set()
        while head in self.config.aliases and head not in seen:
            seen.add(head)
            expansion = self.config.aliases[head].split(None, 1)
            head = expansion[0]
            rest_extra = expansion[1] if len(expansion) > 1 else ""
            rest = f"{rest_extra} {rest}".strip()
        return f"{head} {rest}".strip()
