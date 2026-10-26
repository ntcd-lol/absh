# absh — Absolute Shell for Termux
# -----------------------------------------------------------------------------
# completer.py: Tab completion for commands, files, and absh builtins.
#
# Two caches here exist because both used to run on every keystroke. The merged
# command set (PATH index ∪ aliases) is rebuilt once and reused until its TTL
# lapses or an alias changes; the lexer shares it, so typing the first word of
# a line no longer unions a few thousand names per character. File completion
# is native scandir rather than a `bash -c compgen` subprocess — spawning a
# shell per keystroke is the single slowest thing a completer can do — with a
# short per-directory listing cache to absorb the syscalls while a path is
# typed out. The trade for dropping bash's glob expansion is noted below.
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
import time

from prompt_toolkit.completion import Completer, Completion

from .util import CommandIndex

_CMD_TTL = 30.0
_DIR_TTL = 2.0
_DIR_MAX = 64


class AbshCompleter(Completer):
    def __init__(self, config) -> None:
        self.config = config
        self._index = CommandIndex()
        self._cache: set[str] | None = None
        self._stamp = 0.0
        self._dircache: dict[str, tuple[float, list]] = {}

    def commands(self) -> set[str]:
        """Merged PATH index and aliases, cached across keystrokes."""
        now = time.time()
        if self._cache is None or now - self._stamp > _CMD_TTL:
            names = set(self._index.names())
            names.update(self.config.aliases)
            self._cache = names
            self._stamp = now
        return self._cache

    def invalidate(self) -> None:
        """Drop the command cache; call after aliases change."""
        self._cache = None

    def get_completions(self, document, complete_event):
        text_before = document.text_before_cursor
        parts = text_before.split()
        # Completing the very first word means "command"; anything after means
        # "arguments", where files are the useful thing to offer.
        completing_command = len(parts) == 0 or (
            len(parts) == 1 and not text_before.endswith(" ")
        )

        if completing_command:
            prefix = parts[0] if parts else ""
            yield from self._complete_commands(prefix)
            return

        yield from self._complete_files(document)

    def _complete_commands(self, prefix: str):
        for name in sorted(self.commands()):
            if name.startswith(prefix):
                yield Completion(name, start_position=-len(prefix))

    # -- files ------------------------------------------------------------

    def _complete_files(self, document):
        # Plain prefix match on the last path segment. We forgo bash's glob
        # expansion here; in exchange a keystroke costs one cached scandir
        # instead of a fork+exec, which is what makes typing feel instant.
        token = document.get_word_before_cursor(WORD=True)
        if "/" in token:
            dirpart, namepart = token.rsplit("/", 1)
            base = os.path.expanduser(dirpart + "/")
        else:
            namepart = token
            base = os.getcwd()

        for name, isdir in self._listdir(base):
            if not name.startswith(namepart):
                continue
            # Hidden entries appear only once the user asks for them, matching
            # how compgen/bash treat a leading dot.
            if name.startswith(".") and not namepart.startswith("."):
                continue
            yield Completion(
                name + ("/" if isdir else ""), start_position=-len(namepart)
            )

    def _listdir(self, base: str) -> list[tuple[str, bool]]:
        """Directory entries as (name, is_dir), cached briefly per directory."""
        now = time.time()
        hit = self._dircache.get(base)
        if hit and now - hit[0] < _DIR_TTL:
            return hit[1]
        entries: list[tuple[str, bool]] = []
        try:
            with os.scandir(base) as it:
                for e in it:
                    entries.append((e.name, e.is_dir()))
        except OSError:
            entries = []
        if len(self._dircache) >= _DIR_MAX:
            self._dircache.clear()
        self._dircache[base] = (now, entries)
        return entries
