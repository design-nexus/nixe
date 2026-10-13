# Notepad

A plain-text notepad for [Omarchy](https://omarchy.org), with tabs. It takes its colors
from your Omarchy theme and fits a half-screen tile.

## What it does

- **Tabs:** open as many files as you like, each in its own tab. A dot marks unsaved
  changes. Untitled tabs are named after their first line.
- **Nothing to lose:** closing the window never asks to save. Open tabs, cursor
  positions and unsaved text all come back next time. A tab closed with unsaved
  changes can be brought back with *Undo* or <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>T</kbd>.
- **Formatting:** pick the font and size, line spacing, word wrap, tab width, spaces
  instead of tabs, and a centered 80- or 100-column text width. Line numbers and a
  current-line highlight are optional. Changes apply as you make them, and
  <kbd>Ctrl</kbd>+<kbd>+</kbd>/<kbd>−</kbd> change the size while you type.
- **Find and replace:** <kbd>Ctrl</kbd>+<kbd>F</kbd> highlights every match and counts
  them; <kbd>Ctrl</kbd>+<kbd>H</kbd> replaces one at a time or all at once (one undo).
- **Files stay as they were:** LF or CRLF line endings and file permissions are kept,
  and saves are atomic. Files changed by another program reload on their own, unless
  you have unsaved edits, in which case you're told.
- **Themes:** follows the Omarchy theme live, or pick one of 15 bundled themes, or add
  your own.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/design-nexus/nixe/main/install.sh | bash -s -- notepad
```

It builds from source (installing Rust and GTK 4 with pacman if needed) and installs
to `~/.local`. Add `bash -s -- --bind` to also print a Hyprland binding.
To remove it, run the same line with `uninstall.sh` in place of `install.sh`
(add `bash -s -- --purge` to remove settings and unsaved text too).

## Use

```sh
nixe-notepad [FILE…]           # open files in tabs (a new name is created on the first save)
nixe-notepad --toggle          # open or close the window, for a keybinding
nixe-notepad --section settings
```

Press <kbd>F1</kbd> for every shortcut.

It opens floating and centered: the installer adds a rule for it to
`~/.config/hypr/nixe.lua`.

## Files

| Path | What |
| --- | --- |
| `~/.config/nixe-notepad/settings.toml` | Settings |
| `~/.config/nixe-notepad/themes/*.toml` | Your own themes |
| `~/.local/share/nixe-notepad/session.toml` | Open tabs and recent files |
| `~/.local/share/nixe-notepad/scratch/` | Unsaved text |

## License

MIT
