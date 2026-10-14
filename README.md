# Nixe

Desktop apps for [Omarchy](https://omarchy.org), built with GTK 4 and Rust. They share
one look: a flat, monospace window that takes its colors from your Omarchy theme and
changes with it, fits a half-screen tile, and works from the keyboard.

| App | What it is |
| --- | --- |
| [Glimpse](apps/glimpse) | A local universal search panel with plugins |
| [Settings](apps/settings) | A control panel for Omarchy |
| [Tasks](apps/tasks) | A task manager: processes, usage, startup apps |
| [Torrents](apps/torrents) | A BitTorrent client, built on libtorrent |
| [PDF](apps/pdf) | A PDF viewer and editor |
| [Notepad](apps/notepad) | A plain-text notepad with tabs |
| [Music](apps/music) | A music player for your library, radio and podcasts |
| [Media Player](apps/media-player) | A video player for movies and TV shows |
| [Chat](apps/chat) | A chat client for Ollama |
| [Fonts](apps/fonts) | A font manager for Google Fonts and Nerd Fonts |
| [Archive](apps/archive) | An archive manager, built on 7-Zip |
| [Office](apps/office) | Write, Sheets and Present: documents, spreadsheets and slides |
| [Photos](apps/gallery) | A photo gallery and editor, with a stand-alone Photo Viewer |
| [Assistant](apps/assistant) | A local voice assistant: push-to-talk, wake word, desktop commands (not part of `all`; builds with CUDA when it's there) |

Settings also takes device [extensions](extensions) (ASUS, Logitech, Razer, Corsair, RGB
lighting, headsets, game controllers, drawing tablets, monitors, NVIDIA, webcams,
Stream Decks and the assistant), installed from Settings → Extensions.

## Install

Install the apps you want, or all of them:

```sh
curl -fsSL https://raw.githubusercontent.com/design-nexus/nixe/main/install.sh | bash -s -- music pdf
curl -fsSL https://raw.githubusercontent.com/design-nexus/nixe/main/install.sh | bash -s -- all
```

Only the apps you name are downloaded and built. The installer adds what they need
from the Arch repositories, installs to `~/.local`, and adds the `nixe` command. Add
`--default` to make the apps open their file types.

```sh
nixe list                 # the apps, and which are installed
nixe install chat         # add another
nixe update               # rebuild every installed app from the latest source
nixe uninstall chat       # remove one (--purge also removes its settings and data)
```

## Shared settings

The theme is shared: choose one in any app and the others follow. It is kept in
`~/.config/nixe/theme.toml`, and themes in `~/.config/nixe/themes/` are offered in
every app. Each app keeps its own settings in `~/.config/nixe-<app>/settings.toml`.

Notepad and Archive open as floating windows; their Hyprland rules are in
`~/.config/hypr/nixe.lua`.

## Building

```sh
cargo build --release -p nixe-music     # one app
cargo build --release --workspace       # all of them
./install.sh music                      # build and install from this checkout
```

The shared code is in `crates/`: `nixe-core` (paths, preferences, commands),
`nixe-theme` (themes and the shared stylesheet), `nixe-ui` (widgets, the settings card,
the window frame, the command bar and Inspector) and `nixe-icons` (the app icons). [STYLE.md](STYLE.md)
describes how the apps look and behave.

## License

MIT
