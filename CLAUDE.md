# Nixe umbrella — notes for working on this repo

This repository holds no app source. Apps live in `design-nexus/nixe-<app>`; shared
crates in `nixe-core` (core, accounts, eds, when, sync) and `nixe-design` (theme, ui,
icons, playback, and the canonical `STYLE.md`). Work on an app in its own repo.

- `suite.toml`: every repository and app the suite supports, each pinned to an
  immutable commit (`revision`), with release tags and artifact checksums where a
  release exists. `dependency_revision` is the newest shared commit: dependents lock it
  or an older commit in its history, and move up when they need something newer.
- `install.sh` → `tools/install-suite.py`: installs the apps named (or `all`). With a
  release it downloads and checks the archive; with none it fetches the repository at
  its pinned `revision` and runs that repo's installer (`installer`, default
  `install.sh`). `NIXE_BUILD=1` builds released apps from source too.
- `bin/nixe`: the user command (`list`, `install`, `update`, `uninstall`, `dev`,
  `release`), copied to `~/.local/bin/nixe` by every app's installer. Its `ALL` list
  is what `list` and `update` know; add new apps there and to `suite.toml`.
- `tools/suite.py`: `nixe dev setup|status|build|test` and `nixe release check|notes`
  over sibling checkouts (`.nixe-local.json`, ignored). `release check` also checks
  that every app's lockfile uses the shared crates at the suite's pinned revisions.
- Settings reads this repo's releases and installer for its own updates; Settings'
  extensions live in `nixe-settings/extensions`.
- The pre-split monorepo is in this repository's history at `baseline` in
  `suite.toml`; migration records are `MULTIREPO_MIGRATION.md` and `docs/migration/`.
- Checks: `python3 -m unittest discover -s tools/tests`, `bash -n bin/nixe install.sh`,
  `bin/nixe release check --structure-only`.
