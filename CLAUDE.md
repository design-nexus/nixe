# Nixe — notes for working on this repo

- One Cargo workspace: `apps/*` (one package per app, named `nixe-<app>`) and
  `crates/*`. Each app has its own notes in `apps/<app>/CLAUDE.md`. `STYLE.md` is the
  look and behaviour every app follows.
- Shared crates:
  - `nixe-core`: `app::init` (call first in `main`; it names the app's directories), `control` (the session-bus control interface Nixe Assistant uses: Notepad, Write),
    `paths`, `cmd` (`run`, `spawn`, `background`, `atomic_write`, …), `prefs_store!`
    (the debounced `settings.toml` store; `flush` on quit), `migrate::from` (moves
    `nexus-*` directories from before the rename, leaving links).
  - `nixe-theme`: palettes, bundled and user themes, Follow Omarchy, the suite theme in
    `~/.config/nixe/theme.toml`, and `base.css` (loaded before each app's own
    `style.css`, with `@APP@` replaced by the app's window class; `base_skip` lists the
    shared rules an app styles its own way).
  - `nixe-ui`: `widgets`, `settings_card`, `chrome` (sidebar head, search strip, status
    bar actions, window title), `commandbar` and `inspector` (the document editors' chrome), `keys` (Ctrl+, and ? where an app lacks them),
    `clamp`.
  - `nixe-icons`: the app icons; `make_icons.py` writes them from one template.
- Each app's `paths.rs`, `cmd.rs`, `prefs.rs`, `theme.rs` and `widgets.rs` re-export
  the crates and add only what is the app's own. A local function of the same name
  wins over the re-exported one.
- Names: binaries `nixe-<app>` (Office: `nixe-office` plus `nixe-write`/`-sheets`/
  `-present` scripts; Photos: `nixe-photos` and `nixe-viewer`), app ids
  `io.github.design_nexus.nixe.<App>`, data in `~/.config|.local/share|.local/state|.cache/nixe-<app>`.
  Files from before the rename still open: Office reads `nexus-*` containers, PDF
  reads `Nexus*` annotation keys, Chat imports `nexus-chat` exports.
- `install.sh APP…|all` builds and installs from a checkout, from a sparse clone when
  piped, or from CI releases (`<app>-v<version>` tags, `.github/workflows/release.yml`)
  when every app asked for has one. It removes pre-rename copies, rewrites old desktop
  ids in `mimeapps.list` and writes `~/.config/hypr/nixe.lua`. `apps/<app>/install.sh`
  calls it for that app. `bin/nixe` is the user-facing command.
- Checks: `cargo build --workspace`, `cargo test --workspace` (the code isn't
  rustfmt-clean as a whole; format only what you write). Unit tests that touch paths
  get the neutral `nixe-test` identity, so they never use a real app's files.
- Run a test window with scratch data: `XDG_DATA_HOME=… XDG_CACHE_HOME=… ./target/debug/nixe-<app>`,
  or floating at a size with `hyprctl dispatch "hl.dsp.exec_cmd('[float; size 1280 860] CMD')"`.
- `apps/assistant` (Nixe Assistant) is its own Cargo workspace, excluded from the root
  one with `extensions`: CUDA llama.cpp and ONNX. `./install.sh assistant` runs its
  `scripts/install.sh` (which first moves an install from its old omarchy-assistant name).
- `extensions/` holds Settings' device extensions (catalog `extensions/index.json`,
  installed by Settings from a sparse clone of nixe). Rust ones share `extensions/common`
  (`nixe-ext`: pages, commands, udev access rules, OpenRGB, lighting rows) and its
  `install-rust.sh`; releases are `ext-<id>-v<version>`.
