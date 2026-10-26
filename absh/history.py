# absh — Absolute Shell for Termux
# -----------------------------------------------------------------------------
# history.py: persistent command history and a frecency table for directory jumping.
#
# History lives in ~/.absh/history (plain lines, one per entry) so it stays
# greppable and survives upgrades. The frecency table is a separate JSON file
# because `z` scoring needs timestamps and weights, not just raw lines — mixing
# the two would make the common case (append a command) pay for the rare one.
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

from .config import CONFIG_DIR

HISTORY_PATH = CONFIG_DIR / "history"
FRECENCY_PATH = CONFIG_DIR / "frecency.json"

# A directory's score is the sum of per-visit weights, each decayed by age.
# These buckets are lifted from z's heuristic: a visit this hour counts far
# more than one last month, which is what makes `z` feel like it reads your mind.
_RECENT_HOUR = 4.0
_TODAY = 2.0
_WEEK = 0.5
_MONTH = 0.25


def _weight(age_seconds: float) -> float:
    if age_seconds < 3600:
        return _RECENT_HOUR
    if age_seconds < 86400:
        return _TODAY
    if age_seconds < 604800:
        return _WEEK
    return _MONTH


class History:
    """Command history with a hard cap and de-duplication of consecutive runs."""

    def __init__(self, path: Path = HISTORY_PATH, limit: int = 5000) -> None:
        self.path = path
        self.limit = limit
        self._lines: list[str] = []
        self._load()

    def _load(self) -> None:
        if self.path.is_file():
            self._lines = [
                line.rstrip("\n")
                for line in self.path.read_text(errors="replace").splitlines()
                if line.strip()
            ][-self.limit:]

    def add(self, line: str) -> None:
        line = line.strip()
        if not line or (self._lines and self._lines[-1] == line):
            return
        self._lines.append(line)
        if len(self._lines) > self.limit:
            self._lines = self._lines[-self.limit:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def search(self, query: str, limit: int = 50) -> list[str]:
        """Newest-first matches whose text contains the query."""
        if not query:
            return list(reversed(self._lines[-limit:]))
        hits = [ln for ln in self._lines if query in ln]
        return list(reversed(hits))[:limit]

    def __iter__(self):
        return iter(self._lines)

    def __len__(self) -> int:
        return len(self._lines)


class Frecency:
    """z-style frecency scores for directories, backing the `z` builtin."""

    def __init__(self, path: Path = FRECENCY_PATH) -> None:
        self.path = path
        self._data: dict[str, list[list[float]]] = defaultdict(list)
        self._load()

    def _load(self) -> None:
        if self.path.is_file():
            try:
                raw = json.loads(self.path.read_text())
            except (OSError, json.JSONDecodeError):
                raw = {}
            for dirpath, visits in raw.items():
                self._data[dirpath] = [[float(v[0]), float(v[1])] for v in visits]

    def add(self, dirpath: str, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        visits = self._data[dirpath]
        visits.append([now, 1.0])
        # Cap per-dir history so the file cannot grow without bound on a
        # directory the user lives in; old visits carry almost no weight anyway.
        if len(visits) > 100:
            del visits[:-100]
        self._save()

    def score(self, dirpath: str, now: float | None = None) -> float:
        now = now if now is not None else time.time()
        return sum(_weight(now - v[0]) * v[1] for v in self._data.get(dirpath, []))

    def ranked(self, query: str = "", now: float | None = None) -> list[tuple[str, float]]:
        """Directories sorted by score; `query` fuzzy-matches the path when given."""
        from .util import fuzzy_score

        now = now if now is not None else time.time()
        out = []
        for dirpath in self._data:
            if query and fuzzy_score(query, dirpath) is None:
                continue
            s = self.score(dirpath, now)
            if s > 0:
                out.append((dirpath, s))
        out.sort(key=lambda kv: kv[1], reverse=True)
        return out

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=0))
