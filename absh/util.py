# absh — Absolute Shell for Termux
# -----------------------------------------------------------------------------
# util.py: small shared helpers with no absh dependencies.
#
# Kept dependency-free on purpose: config, executor, completer and the prompt
# all reach in here, so nothing in this file may import from them.
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path


def humanize_duration(seconds: float) -> str:
    """Compact duration for the prompt: 420ms, 3.1s, 2m07s, 1h04m."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(round(seconds)), 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"


def shorten_path(path: str | Path, home: str | None = None) -> str:
    home = home or str(Path.home())
    p = str(path)
    if p == home:
        return "~"
    if p.startswith(home + os.sep):
        return "~" + p[len(home):]
    return p


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def fuzzy_score(query: str, text: str) -> float | None:
    """Subsequence score; higher is better, None when the query does not match."""
    if not query:
        return 0.0
    q, t = query.lower(), text.lower()
    score, ti, last = 0.0, 0, -1
    for ch in q:
        idx = t.find(ch, ti)
        if idx == -1:
            return None
        score += 1.0
        if idx == last + 1:
            score += 2.0                      # contiguous run
        if idx == 0 or t[idx - 1] in "/-_ .":
            score += 1.5                      # word boundary
        last, ti = idx, idx + 1
    score += max(0.0, 10.0 - len(t)) * 0.1    # prefer shorter candidates
    return score


def which_all(name: str) -> list[str]:
    hits = []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d:
            continue
        cand = Path(d) / name
        try:
            if cand.is_file() and os.access(cand, os.X_OK):
                hits.append(str(cand))
        except OSError:
            continue
    return hits


class CommandIndex:
    """Names of every executable on PATH, refreshed when the cache expires."""

    TTL = 300.0

    # Windows keeps the suffix in the listing (git.exe), but a user types the
    # bare name. Strip these so highlighting and completion match what is
    # actually invocable. Irrelevant on Termux, where nothing has a suffix.
    _WIN_SUFFIXES = (".exe", ".com", ".bat", ".cmd")

    def __init__(self) -> None:
        self._names: set[str] = set()
        self._stamp = 0.0

    def names(self) -> set[str]:
        now = time.time()
        if now - self._stamp < self.TTL and self._names:
            return self._names
        found: set[str] = set()
        strip = os.name == "nt"
        for d in os.environ.get("PATH", "").split(os.pathsep):
            if not d:
                continue
            try:
                for entry in os.listdir(d):
                    p = Path(d) / entry
                    if p.is_file() and os.access(p, os.X_OK):
                        found.add(self._bare(entry) if strip else entry)
            except OSError:
                continue
        self._names, self._stamp = found, now
        return self._names

    @classmethod
    def _bare(cls, entry: str) -> str:
        low = entry.lower()
        for suf in cls._WIN_SUFFIXES:
            if low.endswith(suf):
                return entry[: -len(suf)]
        return entry


_git_cache: dict[str, tuple[float, str | None, bool]] = {}


def git_info(cwd: str) -> tuple[str | None, bool]:
    """(branch, dirty) for the repo containing cwd; (None, False) outside one.

    Branch comes from reading .git/HEAD (no subprocess). Dirty needs a real
    status call, so it is cached for a couple of seconds — running git on every
    prompt is what makes shells feel slow on a phone.
    """
    now = time.time()
    cached = _git_cache.get(cwd)
    if cached and now - cached[0] < 2.0:
        return cached[1], cached[2]

    branch = None
    head = _find_git_head(cwd)
    if head is not None:
        try:
            ref = head.read_text().strip()
        except OSError:
            ref = ""
        branch = ref.removeprefix("ref: refs/heads/") if ref else None

    dirty = False
    if branch is not None:
        try:
            out = subprocess.run(
                ["git", "-C", cwd, "status", "--porcelain", "-uno"],
                capture_output=True, text=True, timeout=0.7,
            )
            dirty = bool(out.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            dirty = False

    _git_cache[cwd] = (now, branch, dirty)
    return branch, dirty


def _find_git_head(cwd: str) -> Path | None:
    p = Path(cwd).resolve()
    for directory in [p, *p.parents]:
        head = directory / ".git" / "HEAD"
        if head.is_file():
            return head
    return None
