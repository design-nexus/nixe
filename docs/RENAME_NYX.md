# Renaming Nixe to Nyx

**Status:** approved 2026-10-27 (names as below, brand overlap fine, no transition period,
nothing published in stores, GitHub repos to be renamed). Do it as its own sweep **before** moving more apps
to Design 2.0: only Settings and Files are on 2.0 so far, and the new 2.0 config files
(`~/.config/nixe/themes/`, `theme.toml`'s `[app_accents]`) then move only once.

## 1. Decisions to confirm first

| Thing | Today | Proposed |
| --- | --- | --- |
| Suite name (docs, UI text) | Nixe | **Nyx** |
| App display names | Files, Mail, … | unchanged ("Files"); suite text says "Nyx" |
| Repositories | `design-nexus/nixe-<app>`, `nixe`, `nixe-core`, `nixe-design` | `design-nexus/nyx-<app>`, `nyx`, `nyx-core`, `nyx-design` |
| Rust crates | `nixe-core`, `nixe-theme`, `nixe-ui`, `nixe-icons`, `nixe-playback`, `nixe-accounts`, `nixe-eds`, `nixe-sync`, `nixe-when` | `nyx-*` (module paths `nyx_core::…`) |
| Binaries | `nixe-<app>` (67 installed), `nixe` CLI | `nyx-<app>`, `nyx` |
| App IDs, desktop files, icons | `io.github.design_nexus.nixe.<App>` | `io.github.design_nexus.nyx.<App>` (the org part stays) |
| D-Bus names | `…nixe.Control`, `Passwords1`, `Cloud1`, `Transfer1`, `MailEngine1`, `Files.FileManager1` | `…nyx.*` |
| User data | `~/.config/nixe-<app>`, `~/.config/nixe/` (suite), same under share/state/cache | `nyx-<app>`, `nyx/` |
| systemd user units | `nixe-*.service` (13) | `nyx-*.service` |
| Root helpers, polkit | `/usr/local/lib/nixe-{assistant,settings,store}`, `…nixe.{store,assistant}.policy` | `nyx-*` |
| Env vars (build/test) | `NIXE_*` (~20 names) | `NYX_*` |
| Hyprland rules | `~/.config/hypr/nixe.lua` | `nyx.lua` |

- **Name collision:** "Nyx" is used by other Linux projects (Chaotic-Nyx and others). Binaries are
  `nyx-<app>` and the IDs are namespaced, so there is no technical clash. The overlap is accepted.
- **No transition period:** old names (commands, D-Bus names, the old Passwords browser host) stop
  working at the switch. Nothing is published in a store, so only this machine needs migrating.

## 2. What carries the name (inventory)

- **37 repositories** with about 11,500 mentions in tracked files: the umbrella (~1,200), Assistant (~750),
  Passwords (~630) and Settings (~600) carry the most.
- **About 60 reverse-DNS identifiers:**
  - app IDs and desktop files;
  - D-Bus interfaces and services;
  - two polkit policies;
  - the Passwords native-messaging host `io.github.design_nexus.nixe.passwords`, which the browser
    extension refers to.
- **Keyring items:**
  - Passwords tags secrets with `application nixe-passwords`;
  - `nixe-sync` stores Nextcloud credentials with its own `secret-tool` attributes.

  Renaming these attributes without migrating the items loses access to them.
- **On this machine:**
  - **User data and binaries:** 35 `~/.config/nixe*` folders, matching data, state and cache
    folders, 67 binaries, 35 desktop files and 3 D-Bus services.
  - **systemd:** 13 user units.
  - **Hyprland and Omarchy:** `hypr/nixe.lua`, 6 lines in `hypr/bindings.lua`, the Omarchy bar gear in
    `omarchy/shell.json`, and an Omarchy theme hook `hooks/theme-set.d/50-settings-theme`.
  - **Default apps:** 81 entries in `mimeapps.list`.
- **About 110 user-visible "Nixe" strings in Rust** (Settings → "Nixe apps", window groups, messages),
  plus every README, AGENTS.md and the STYLE.md.
- **Released artifacts** recorded in `suite.toml` keep their old names: they are history. New releases
  use the new names.

## 3. Approach

A scripted, reviewable sweep, done in dependency order. The repo histories stay intact: renames are
commits, not rewrites. Nothing is installed until a stage's checks pass.

1. **Rename tool** (`nyx/tools/rename.py`, run from the umbrella):
   - an ordered table of exact replacements, longest first:
     - `io.github.design_nexus.nixe.` → `…nyx.`
     - `nixe-` → `nyx-`, `nixe_` → `nyx_`
     - `NIXE_` → `NYX_`
     - `Nixe` → `Nyx`, `nixe` → `nyx`
   - an allow-list of files to skip: `Cargo.lock` (regenerated), `dist/`, released checksums,
     `suite.toml`'s artifact fields, and `UPSTREAM.md`/licence notices;
   - file and directory renames (`nixe.lua`, `crates/nixe-theme/`, icons and desktop files named by
     app ID);
   - **dry-run first:** prints every change per repo for review, then applies them on each repo's current branch.
2. **Shared crates first:** `nixe-core` → `nyx-core`, then `nixe-design` → `nyx-design`. Each gets
   built, tested and pushed, and its new revisions are recorded.
3. **Migration code**, in `nyx-core`, before any app moves (see §4).
4. **Apps:** Settings and Files first (the 2.0 pilots), then the rest in any order. Each app:
   - run the rename tool;
   - point it at the new shared crates;
   - add a one-line migration call at startup;
   - build and run its tests;
   - install, open it once on the virtual monitor, check, commit.
5. **Umbrella last:** `suite.toml` (repository names and URLs; historical artifacts untouched), the
   `nyx` CLI, the installer and uninstaller, docs.
6. **GitHub:** rename each repository (`gh repo rename`), after confirming with you. GitHub redirects the
   old URLs, but every `Cargo.toml` and installer is switched to the new URLs in step 1 anyway.
7. **Your machine:** install the suite under the new names, run the one-off desktop migration (§4.4),
   check everything opens with your settings, then remove the leftovers after the transition period.

## 4. Migration and compatibility

### 4.1 User data

- `nyx_core::migrate::from(&["nixe-<app>"])` already exists. It moves `~/.config`, `~/.local/share`,
  `~/.local/state` and `~/.cache` folders and leaves a symlink behind, so older tools still find them.
  Each app calls it at startup.
- **New in `nyx-core`:**
  - `migrate::suite()` moves `~/.config/nixe` (theme.toml, `themes/`) to `~/.config/nyx`, once, with
    the same symlink.
  - Inside moved config files, rewrite the values that name the old suite: theme ids are unaffected,
    but any stored `nixe-…` paths are rewritten.

### 4.2 Keyring

- **Passwords and `nyx-sync`:**
  - on first start, look up items with the old attributes;
  - store each one again with the new attributes;
  - delete the old item only after the new one reads back.
- The migration is idempotent and logged. The uninstaller's `--purge` clears both attribute sets during
  the transition.

### 4.3 Interfaces other programs use

- **D-Bus:** daemons and their clients switch names together (Control, Passwords1, Cloud1, Transfer1,
  MailEngine1, FileManager1), so they are renamed and installed in the same batch.
- **Passwords browser extension:** the extension and its native-messaging manifest switch to
  `…nyx.passwords` together; the old manifest is removed. Reload the unpacked extension afterwards.
- **Glimpse plugins and Notes Control:** plugins that call the Control interface are renamed with it.
- **Commands:** no `nixe-*` aliases. Launchers, keybindings and scripts are updated by §4.4.

### 4.4 Desktop integration (one-off script, `nyx migrate-desktop`, with backups)

1. **systemd:** install `nyx-*.service`, stop and disable `nixe-*.service`, enable the new units, remove
   the old unit files and drop-ins (`nixe-assistantd.service.d` moves with its unit).
2. **Default apps:** in `mimeapps.list`, rewrite `io.github.design_nexus.nixe.*.desktop` →
   `…nyx.*.desktop`, keeping a `.nyx-bak` copy.
3. **Hyprland and Omarchy:**
   - `hypr/nixe.lua` → `nyx.lua`, with its window-class matches updated, since classes are app IDs;
   - update the `require`/source line in `hyprland.lua`;
   - the 6 `bindings.lua` lines;
   - `omarchy/shell.json` (the Settings gear);
   - the Omarchy hook `50-settings-theme`.
4. **D-Bus services:** `~/.local/share/dbus-1/services/…nixe.*.service` → `…nyx.*`.
5. **Root helpers and polkit (needs `sudo`, run by you):** `sudo nyx-settings --install-helper`, and the
   same for Store and Assistant. Then remove `/usr/local/lib/nixe-*` and the two old policies.

### 4.5 Rollback

- Before the desktop migration, archive your Nixe data and config, the way
  `nixe-pre-rename-backup-20261013.tar.gz` did last time.
- Each repo is committed only after it builds and its tests pass; the pre-rename commit is the way back.
- The old binaries stay installed until you confirm.

## 5. Order and checkpoints

| Step | Done when |
| --- | --- |
| Rename tool + dry run over all 37 repos | You've seen the per-repo change summary and the skip list |
| `nyx-core` (with `migrate::suite`, keyring helpers) | Builds; migration tests pass on a scratch `$HOME` |
| `nyx-design` | Builds; `check_css` passes; tests pass |
| Settings, Files | Build, tests, install; they open with your existing settings and theme |
| Remaining 33 apps | Same, a few at a time; daemons (Assistant, Passwords, Mail, Cloud, Transfer, Glimpse) checked for their D-Bus names and units |
| Umbrella (`nyx`) | Installer installs the suite from the new repos; `suite.py` checks pass |
| GitHub renames | After your OK; old URLs redirect |
| Desktop migration on your machine | Everything opens; default apps, keybindings, bar gear and services work |
| Cleanup | Old binaries, units, desktop files and data symlinks removed after you confirm |

## 6. Risks

- **Passwords:** keyring items and the browser extension are the only places where a mistake loses
  access or breaks something outside the suite. Their migration gets tested first on a scratch keyring,
  and nothing old is deleted until the new copy reads back.
- **Missed references:** dynamic strings (`format!("nixe-{app}")`, shell `${…}`) won't match a literal
  search. The dry run also greps the built binaries and installed files for leftover "nixe".
- **Two names at once:** with no aliases, an app on the new names can't reach a daemon still on the old
  ones. Daemons and their clients are renamed and installed in the same batch.
- **Release tooling:** `suite.toml` checks (`tools/suite.py`) and release workflows have the name in
  them. No releases happen during the rename (development is commit-and-push only).

## 7. Needs you

1. Run the `sudo` helper reinstall (§4.4, step 5).
2. Reload the Passwords browser extension after the switch.
