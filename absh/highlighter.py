# absh — Absolute Shell for Termux
# -----------------------------------------------------------------------------
# highlighter.py: live syntax highlighting for the input line.
#
# A hand-rolled prompt_toolkit Lexer rather than Pygments: Pygments ships a
# heavy shell lexer whose token stream we would just be filtering down to the
# handful of colours a phone screen can actually distinguish. This walks the
# line once with regexes and emits the roles theme.py knows about.
# -----------------------------------------------------------------------------

from __future__ import annotations

import re

from prompt_toolkit.lexers import Lexer

# Shell keywords/operators worth colouring separately. The rest is plain.
_OPERATORS = r"(?:\|\||&&|[|&;<>]|\$\(|\)|\()"
_KEYWORDS = {"if", "then", "else", "elif", "fi", "for", "while", "until", "do",
             "done", "case", "esac", "function", "in", "select", "time"}

_WORD = r"[A-Za-z_][A-Za-z0-9_.-]*"


class ShellLexer(Lexer):
    """Colour a command line: operators, vars, strings, comments, flags, commands."""

    def __init__(self, command_names: callable = None) -> None:
        # Callable returning the set of known command names; the completer owns
        # the PATH index and we borrow it rather than building a second copy.
        self.command_names = command_names

    def lex_document(self, document):
        text = document.text
        lines = text.split("\n")

        def get_tokens(lineno: int):
            if 0 <= lineno < len(lines):
                return self._lex_line(lines[lineno])
            return []

        return get_tokens

    def _lex_line(self, line: str):
        tokens: list[tuple[str, str]] = []
        pos = 0
        first_word = True
        patterns = [
            ("comment", re.compile(r"#.*$")),
            ("string", re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")),
            ("var", re.compile(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|\$\?|\$\d")),
            ("operator", re.compile(_OPERATORS)),
            ("path", re.compile(r"(?:~|\.{1,2})/[^\s|&;<>]*")),
            ("word", re.compile(_WORD + r"|[0-9]+")),
            ("skip", re.compile(r"\s+")),
        ]

        while pos < len(line):
            for kind, rx in patterns:
                m = rx.match(line, pos)
                if not m:
                    continue
                value = m.group()
                if kind == "skip":
                    tokens.append(("class:plain", value))
                elif kind == "word":
                    tokens.append((self._word_class(value, first_word), value))
                    first_word = False
                elif kind == "operator":
                    # An operator resets "first word", so `a | b` colours b as a
                    # command too — matching how the line will actually parse.
                    tokens.append(("class:operator", value))
                    first_word = True
                else:
                    tokens.append((f"class:{kind}", value))
                pos = m.end()
                break
            else:
                tokens.append(("class:plain", line[pos]))
                pos += 1
        return tokens

    def _word_class(self, word: str, first_word: bool) -> str:
        if word.startswith("-"):
            return "class:flag"
        if word in _KEYWORDS:
            return "class:builtin"
        if first_word:
            known = self.command_names() if self.command_names else None
            if known is not None and word not in known:
                return "class:cmd_unknown"
            return "class:cmd"
        return "class:plain"
