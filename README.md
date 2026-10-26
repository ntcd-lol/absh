<div id="logo" align="center">
    <br />
    <img src="./assets/logo.svg" alt="absh" width="200"/>
    <h1>absh</h1>
    <h3>Absolute Shell for Termux.</h3>
</div>

> [!NOTE]
> In active development. API and builtins may change.

`absh` is an interactive shell for [Termux](https://termux.dev) that keeps the
power of `bash` while wrapping it in the quality-of-life features modern shells
ship with: live syntax highlighting, autosuggestions, a two-line status prompt
with git and battery info, a frecency directory jumper, and colour themes you
can switch with a single command.

It is **not** a bash replacement. Everything you type that isn't an `absh`
builtin runs through a real `bash -c`, so pipes, globs, redirects, your
aliases, functions and `PATH` all behave exactly as you expect. absh adds a
smart editor and prompt *around* bash rather than trying to out-implement it.

## Features

- **Live syntax highlighting** — commands, flags, strings, variables and
  operators are coloured as you type, and an unknown command is flagged before
  you press enter.
- **Autosuggestions** — accept a ghosted suggestion from your history with
  `→`, or keep typing to ignore it.
- **Two-line prompt** — current directory (with `~` collapsed), git branch and
  dirty marker, battery percentage, clock, and the exit code of the last
  command. Battery flips to red below 20%.
- **`z` — jump to frecent directories** — absh learns which directories you
  actually use and weights recent visits heavily. `z proj` jumps to the best
  match.
- **Themes** — `theme sunset`, `theme matrix`, `theme mono` and more, saved
  across sessions.
- **Notifications for long commands** — when a command runs longer than a
  configurable threshold, absh fires a `termux-toast` and a light vibration so
  you know it finished without watching the screen. With streaming enabled the
  toast also carries the last line of output.
- **Streaming output** — command output is forwarded line by line as it
  arrives, and the tail is kept for the completion notification. Terminal-only
  programs (`vim`, `ssh`, `python`, …) are detected and handed the real
  terminal instead; set `stream_output = false` to opt out entirely.
- **History search** — `Ctrl+R` reverse-searches your persistent history.

## Install

Requires Termux and Python 3.9+.

```sh
pkg install python git
git clone https://github.com/ntcd-lol/absh
cd absh
pip install .
```

Then just run it:

```sh
absh
```

You can also run it without installing:

```sh
python -m absh
```

For battery stats and toast notifications, install the Termux API package and
the companion app:

```sh
pkg install termux-api
```

`absh` works fine without it — those prompt segments and notifications are
skipped automatically.

## Builtins

These are handled by absh itself (everything else runs in `bash`):

| Command | What it does |
| --- | --- |
| `theme [name\|--list]` | Switch the colour theme; with no argument, list themes. The choice is saved. |
| `z [query]` | Jump to the most frecent directory matching `query`. |
| `alias [name=value]` | List, create, or `--del` an alias. Persisted to the config. |
| `reload` | Re-read `~/.absh/config.toml`. |
| `help` | Show this list. |
| `exit` | Leave the shell. |

Plus the stateful ones you'd miss if they weren't there: `cd` (including
`cd -`), `export`, `unset`.

## Configuration

absh reads `~/.absh/config.toml`, creating it with sensible defaults on first
run:

```toml
[general]
theme = "aurora"
notify_after = 8        # seconds; 0 disables the long-command toast
show_battery = true
show_time = true
stream_output = true    # pipe output live; false hands programs the real terminal

[ui]
toolbar = true
autosuggest = true
highlight = true

[aliases]
ll = "ls -la"
```

History lives in `~/.absh/history` and the `z` frecency data in
`~/.absh/frecency.json`.

## Keybindings

| Key | Action |
| --- | --- |
| `Ctrl+R` | Reverse-search history. |
| `Ctrl+C` | Cancel the current line. |
| `Ctrl+D` | Exit on an empty line, delete a character otherwise. |
| `→` | Accept the autosuggestion. |
| `Tab` | Complete a command, file or directory. |

## License

MIT.

<!--- Насколько я помню, мое число как и твое - начинается на 4, но заканчивается иначе. Может это и есть стартовый вектор? --->
<!--- А еще я помню как ты любишь копаться в байтах --->
<!---
    ???:
Помни: Не доверяй сплошмя каждому комментарию.
--->
