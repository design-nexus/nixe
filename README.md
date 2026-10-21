# Nixe

Desktop apps for [Omarchy](https://omarchy.org), built with GTK 4 and Rust. They share
one look: a flat, monospace window that takes its colors from your Omarchy theme and
changes with it, fits a half-screen tile, and works from the keyboard.

| App | What it is |
| --- | --- |
| [Glimpse](https://github.com/design-nexus/nixe-glimpse) | A local universal search panel with plugins |
| [Store](https://github.com/design-nexus/nixe-store) | Discover, install and update apps from Omarchy, Arch, AUR and custom sources |
| [Settings](https://github.com/design-nexus/nixe-settings) | A control panel for Omarchy |
| [Git](https://github.com/design-nexus/nixe-git) | Native Git client: visual commit graph, diffs, staging, branches and stashes |
| [Passwords](https://github.com/design-nexus/nixe-passwords) | A password manager for your Vaultwarden server: logins, one-time codes and secure notes |
| [Contacts](https://github.com/design-nexus/nixe-contacts) | A local address book: contacts, favorites, lists, birthdays and import/export |
| [Tasks](https://github.com/design-nexus/nixe-tasks) | A task manager: processes, usage, startup apps |
| [Torrents](https://github.com/design-nexus/nixe-torrents) | A BitTorrent client, built on libtorrent |
| [PDF](https://github.com/design-nexus/nixe-pdf) | A PDF viewer and editor |
| [Notepad](https://github.com/design-nexus/nixe-notepad) | A plain-text notepad with tabs |
| [Music](https://github.com/design-nexus/nixe-music) | A music player for your library, radio and podcasts |
| [Media Player](https://github.com/design-nexus/nixe-media-player) | A video player for movies and TV shows |
| [Theater](https://github.com/design-nexus/nixe-theater) | Your Plex and Jellyfin movies and shows together |
| [Chat](https://github.com/design-nexus/nixe-chat) | A chat client for Ollama |
| [Fonts](https://github.com/design-nexus/nixe-fonts) | A font manager for Google Fonts and Nerd Fonts |
| [Archive](https://github.com/design-nexus/nixe-archive) | An archive manager, built on 7-Zip |
| [Office](https://github.com/design-nexus/nixe-office) | Write, Sheets and Present: documents, spreadsheets and slides |
| [Photos](https://github.com/design-nexus/nixe-photos) | A photo gallery and editor, with a stand-alone Photo Viewer |
| [Weather](https://github.com/design-nexus/nixe-weather) | Forecasts, radar, hourly conditions, air quality and severe-weather alerts |
| [News](https://github.com/design-nexus/nixe-news) | A local RSS, Atom, and JSON Feed reader |
| [Capture](https://github.com/design-nexus/nixe-capture) | Screenshots, annotation, and OCR |
| [Containers](https://github.com/design-nexus/nixe-containers) | Incus and Docker: containers, VMs, Compose, images, networks, volumes |
| [Assistant](https://github.com/design-nexus/nixe-assistant) | A local voice assistant: push-to-talk, wake word, desktop commands (not part of `all`; builds with CUDA when it's there) |

Settings also takes device [extensions](https://github.com/design-nexus/nixe-settings/tree/main/extensions) (ASUS, Logitech, Razer, Corsair, RGB
lighting, headsets, game controllers, drawing tablets, monitors, NVIDIA, webcams,
Stream Decks and the assistant), installed from Settings → Extensions.

## Install

Install the apps you want, or all of them:

```sh
curl -fsSL https://raw.githubusercontent.com/design-nexus/nixe/main/install.sh | bash -s -- music pdf
curl -fsSL https://raw.githubusercontent.com/design-nexus/nixe/main/install.sh | bash -s -- all
```

Only the apps you name are downloaded. Archives are verified against the suite manifest.
Use `NIXE_BUILD=1` for a source build. The installer adds what the apps need
from the Arch repositories, installs to `~/.local`, and adds the `nixe` command. Add
`--default` to make the apps open their file types.

```sh
nixe list                 # the apps, and which are installed
nixe install chat         # add another
nixe update               # install supported releases for installed apps
nixe uninstall chat       # remove one (--purge also removes its settings and data)
```

## Shared settings

The theme is shared: choose one in any app and the others follow. It is kept in
`~/.config/nixe/theme.toml`, and themes in `~/.config/nixe/themes/` are offered in
every app. Each app keeps its own settings in `~/.config/nixe-<app>/settings.toml`.

Notepad, Archive and Weather open as floating windows; their Hyprland rules are in
`~/.config/hypr/nixe.lua`.

## Building

```sh
bin/nixe dev setup
bin/nixe dev build music
bin/nixe dev test music
bin/nixe release check --structure-only
```

Source ownership and immutable shared dependencies are recorded in `suite.toml`.
[Core](https://github.com/design-nexus/nixe-core) contains the shared application,
account and sync foundation. [Design](https://github.com/design-nexus/nixe-design)
contains GTK widgets, themes, icons and playback controls. Its
[STYLE.md](https://github.com/design-nexus/nixe-design/blob/main/STYLE.md) is canonical.
The root Cargo workspace is retained only for rollback; active application work
belongs in the independent checkouts. [Release procedures](docs/RELEASES.md) cover
pinned build inputs, artifacts, CI and coordinated API changes.

## License

MIT

## Multi-repository development

[Migration audit and rollout](MULTIREPO_MIGRATION.md) records the reviewed baseline,
repository boundaries, history-preserving commands, and all 24 independently released applications.
Shared workspaces: [Core](https://github.com/design-nexus/nixe-core) and
[Design](https://github.com/design-nexus/nixe-design).
Installation and updates use checksummed releases from the owning repositories.
The original workspace remains a frozen rollback copy (`NIXE_LEGACY=1`).

```sh
bin/nixe dev status
bin/nixe dev build archive
bin/nixe dev test archive
bin/nixe release check --structure-only
```

`suite.toml` pins repository revisions and application mappings. `.nixe-local.json`
(ignored) overrides local checkout locations. By default, `nixe dev setup` places
repositories beside this umbrella checkout (for example, `~/Projects/nixe-core`).
`NIXE_DEV_HOME` selects a different clone directory. Source publication is recorded in
[the publication receipt](docs/migration/publication.json). `nixe release check`
checks supported releases, source compatibility, artifacts, and checksums.
Build inputs are pinned in `build-environment.json`; runtime/GUI/provider behavior
retains its existing contracts and is not exercised by routine migration checks.
