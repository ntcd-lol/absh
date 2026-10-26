# absh — Absolute Shell for Termux
# -----------------------------------------------------------------------------
# __main__.py: `python -m absh` entry point.
#
# Kept to a one-liner so the module runs identically whether invoked as
# `python -m absh` or through the installed `absh` console script.
# -----------------------------------------------------------------------------

from .shell import main

if __name__ == "__main__":
    raise SystemExit(main())
