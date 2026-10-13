# Fonts — notes for working on this repo

- GTK4 (gtk4-rs 0.11) + Rust. No libadwaita. Follows `STYLE.md`; the theme, widgets,
  settings card and window frame come from the `nixe-*` crates. Every colour is a `@theme_*` token.
- Pages (`sections/`) all use `sections/browse.rs`: a toolbar (filter, optional chips row
  → `.list-toolbar.stacked`), a `FontTable` (`fonttable.rs`) and a `PreviewPanel` in a
  vertical `Paned`. Ctrl+F focuses the visible page's `.page-search`; Ctrl+K the search strip
  over the page (Search page, both catalogs), also opened from the sidebar's head.
- Catalogs (`catalog/`): Google `fonts.google.com/metadata/fonts` (popularity/trending
  are ranks, lower = more popular) and the download manifest
  `fonts.google.com/download/list?family=` (strip `)]}'`). Nerd Fonts: `fonts.json` in the
  repo + the latest release tag; archives are `<folderName>.tar.xz`. Raw JSON is cached
  in `~/.cache/nixe-fonts/` and refetched after 24 h (`prefs.catalog_fetched`).
- `events.rs` is the change bus (Catalog, Installed, Jobs); subscribers live as long as
  their widget. The status column updates bound labels in place (no row rebuilds).
- `install.rs`: one worker thread, jobs in order, results over async-channel. Installs
  stage in a hidden `.Family.part-PID` folder beside the target and swap it in.
  `installed.rs` records files in `~/.local/state/nixe-fonts/installed.toml`; only
  paths under `~/.local/share/fonts/nixe-fonts` are ever deleted.
- Previews (`preview.rs`): one file per family in `~/.cache/nixe-fonts/preview/`, drawn
  through its own `FcConfig` + `PangoCairoFcFontMap` set with `widget.set_font_map`.
  With one font in the map, every family request falls back to it. The Nerd icons line
  sits outside that box so it uses the window's fonts.
- Checks: `cargo clippy --all-targets -- -D warnings`, `cargo test`. The network
  install test: `cargo test -- --ignored installs_and_removes` (scratch XDG dirs).
  Visual check: `FONTS_SNAPSHOT=/tmp/x.png fonts --section nerd` (quit a running
  instance first; it's single-instance).
