---
name: absh-comment-style
description: Comment and code style profile for absh (Absolute Shell for Termux); read before writing or rewriting code there
updated: 2026-10-26
---

# Comment style: absh

## General
- Comment language: English (identifiers and technical terms in English)
- Density: moderate — explain only the non-obvious (subprocess, ANSI/escape, prompt_toolkit, caching); leave trivial code bare
- Avoid: emoji, section-divider banners inside files, commented-out code, narrating ("Now we...")

## Tier A: large opening comment (file/module header)
- Used: every module — a full banner
- Contents: module name, one-line purpose, and the *reason* for a non-obvious design decision if the module has one
- Syntax: `#` block framed by `# ---...---` rules
- Size: ~6-9 lines
- Example:
  ```python
  # absh — Absolute Shell for Termux
  # -----------------------------------------------------------------------------
  # executor.py: turn one input line into a running process.
  #
  # The model is deliberate: absh is a smart line editor on top of bash, not a
  # bash clone. Stateful builtins a user expects to persist (cd, export, alias)
  # are handled in-process; everything else goes to a real `bash -c` so pipes,
  # globs and redirects behave exactly as bash does them.
  # -----------------------------------------------------------------------------
  ```

## Tier B: 3-line explanatory comment
- When: caching decisions, terminal/escape quirks, one-off workarounds
- Voice: why / constraint; impersonal
- Syntax: hash lines, wrapped
- Example:
  ```python
  # Branch comes from reading .git/HEAD (no subprocess). Dirty needs a real
  # status call, so it is cached for a couple of seconds — running git on
  # every prompt is what makes shells feel slow on a phone.
  ```

## Tier C: 1-line brief comment
- Position: above the line, occasionally trailing
- Form: lowercase, no final period; states the fact
- Frequency: common for small local facts
- Example:
  ```python
  score += max(0.0, 10.0 - len(t)) * 0.1    # prefer shorter candidates
  ```

## Docstrings
- Format: Google-style, short
- Required for: public functions/classes only; never restate the signature (no tautologies)

## Markers
- TODO/FIXME format: `TODO(name): text`

## Other
- Naming: names scale with scope — short in small scopes, descriptive in module-level API
- Commit messages: short imperative subject; body only for the why
