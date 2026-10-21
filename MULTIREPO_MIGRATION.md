# Nixe multi-repository migration

## Baseline and current implementation

Reviewed source: `design-nexus/nixe`, branch `main`, commit
`97c1899499e52a42f6eaddca188aac4eca32b96e` (381 commits). At the start of
implementation the checkout was clean and matched GitHub. The original monorepo,
application source, root Cargo workspace, tags, and existing install/update routes
remain intact. Publication was explicitly approved after local preparation and
validation. The source publication receipt is
[docs/migration/publication.json](docs/migration/publication.json).

The initial local foundation/Archive pilot is prepared in
`/home/ken/Projects/nixe-migration-97c1899-reviewed/`:

- `nixe-core`: existing application foundation, GOA/EDS account discovery, and sync.
- `nixe-design`: canonical STYLE.md, themes, GTK widgets, and application icons.
- `nixe-archive`: independent Archive application, installer, and release packaging.
- `nixe-before.bundle`: verified complete backup of all original refs.
- `*-commit-map.txt`: original-to-extracted commit correspondence.
- `pilot.json`: immutable prepared revisions and local repository locations.

The initial receipt is [docs/migration/pilot.json](docs/migration/pilot.json).
The continuation prepares all remaining applications in
`/home/ken/Projects/nixe-migration-97c1899-apps-complete/`. Active checkout and
exported-library revisions are recorded in suite.toml and
[docs/migration/repositories.json](docs/migration/repositories.json). All 23
applications now have independent local repositories; application source in the
original monorepo remains intact. Build/install results are tracked in
[docs/migration/application-validation.json](docs/migration/application-validation.json).
The machine-readable source inventory and direct internal dependency edges are in
[docs/migration/inventory.json](docs/migration/inventory.json). Preparation keeps
registry dependencies from the original lockfile; only Git sources and the reduced
workspace closure change. Published consumers use immutable GitHub commits;
binary artifacts remain pre-publication validation snapshots until rebuilt and released.

## Audit findings

The main Cargo workspace uses resolver 3 and Rust edition 2024, with `apps/*` and
`crates/*`. Assistant is an excluded 15-member workspace using edition 2021.
Device extensions and Glimpse inference also have independent builds. No submodules
were present. The original repository has 16 application release tags and additional
local Assistant branches; the full-ref bundle preserves those branches too.

`STYLE.md` defines existing visual behavior. `nixe-theme`, `nixe-ui`, and
`nixe-icons` already implement shared themes, CSS, widgets, and assets. App-local
paths/cmd/theme/widgets modules often re-export shared implementations and add
application behavior; those wrappers are intentional, not automatic extraction
candidates. `nixe-icons` currently has a placeholder Rust library; the SVG files and
generator are its useful assets.

The existing release workflow handles `*-v*` tags in a rolling Arch container. It
builds monorepo-shaped archives and has no independent PR or cross-repository
compatibility pipeline. Git has a PKGBUILD. Root install.sh supports both source
builds and prebuilt archives, sparse-checks out the monorepo, installs to ~/.local,
and manages integration resources. App install wrappers delegate to this script.

`bin/nixe`, Settings self-updates, extension catalogs/installers, and Glimpse's
catalog contain umbrella URLs or monorepo paths. Keep those entry points until the
corresponding replacement is released. Never switch all applications at once.

Existing account integration is real: `nixe-accounts` serves Settings and Contacts;
`nixe-goa-helper` isolates libgoa-backend in a process separate from Settings.
Contacts keeps its local database and supports read-only EDS account books. This
does not mean remote synchronization exists for every service advertised by GOA.

Mail, Calendar, Reminders, Drive, Maps, and Containers are not existing standalone
applications. Assistant abilities and account service types do not establish those
application repositories. Tasks is a process manager.

## Final repository inventory and mapping

All target repositories are under `design-nexus`. Keep crate/package/binary names,
plain application display names, stable IDs, data paths, and protocol names.
Retain app directories inside their new workspaces to minimize path changes.

| Repository | Current directories and ownership |
| --- | --- |
| nixe | Documentation, suite.toml, CLI, integration/release coordination, compatibility installers; all original history |
| nixe-core | crates/nixe-core, crates/nixe-accounts, crates/nixe-sync |
| nixe-design | STYLE.md, crates/nixe-theme, crates/nixe-ui, crates/nixe-icons, crates/nixe-playback |
| nixe-archive | apps/archive |
| nixe-assistant | Entire apps/assistant workspace, services, abilities, plugins, tooling |
| nixe-capture | apps/capture, apps/capture-glimpse, crates/nixe-capture-core |
| nixe-chat | apps/chat |
| nixe-contacts | apps/contacts |
| nixe-fonts | apps/fonts |
| nixe-photos | apps/gallery; Photos and Photo Viewer together |
| nixe-git | apps/git, including PKGBUILD |
| nixe-glimpse | apps/glimpse, inference and examples, crates/glimpse-plugin-sdk |
| nixe-media-player | apps/media-player |
| nixe-music | apps/music |
| nixe-news | apps/news, apps/news-glimpse, crates/nixe-news-core |
| nixe-notepad | apps/notepad |
| nixe-office | apps/office; Write, Sheets, Present together |
| nixe-passwords | apps/passwords, crates/nixe-passwords-core, crates/nixe-passwords-proto; browser and daemon components together |
| nixe-pdf | apps/pdf |
| nixe-pulse | apps/pulse, apps/pulse-glimpse, crates/nixe-telegram-core, crates/nixe-telegram-calls |
| nixe-settings | apps/settings, crates/nixe-goa-helper, complete extensions/ tree and catalogs |
| nixe-store | apps/store |
| nixe-tasks | apps/tasks |
| nixe-theater | apps/theater, crates/nixe-media-model, crates/nixe-media-cache, crates/nixe-plex, crates/nixe-jellyfin |
| nixe-torrents | apps/torrents and native integration |
| nixe-weather | apps/weather, crates/nixe-weather-core, bundled plugin |

Defer nixe-sdk and nixe-pim. Preserve application-owned public integration crates
instead of prematurely centralizing them. Do not introduce speculative common,
config, storage, search, permissions, or IPC crates.

## Dependency graph and API boundaries

Arrows mean depends on:

```text
nixe-theme -> nixe-core
nixe-ui -> nixe-theme + nixe-core
nixe-icons -> no Rust dependencies

GTK apps -> nixe-core + nixe-theme + nixe-ui
Settings + Contacts -> nixe-accounts
Settings -> nixe-goa-helper executable
News + News plugin -> nixe-news-core -> nixe-sync
Capture + Capture plugin -> nixe-capture-core
Glimpse + News/Capture/Pulse plugins -> glimpse-plugin-sdk
Glimpse + Passwords -> nixe-passwords-proto
Media Player + Theater -> nixe-playback -> nixe-core + nixe-ui
Theater provider/cache crates -> nixe-media-model
Device extensions -> nixe-ext where already used
```

Application-owned public crates may be consumed across repositories. Private
application modules may not. Independently clone/build applications with locked,
immutable Git dependencies; local Cargo patches are optional development overrides.

Preserve `io.github.design_nexus.nixe.Control`, the Passwords1 D-Bus interface,
existing plugin handshakes, browser native-host identities, service definitions,
polkit helpers, XDG paths, configuration formats, and data migration behavior.
Glimpse mounts News/Capture databases read-only: establish explicit schema-version
compatibility before moving those consumers. Keep shared video playback controls
consistent between Media Player and Theater.

Shared playback is now owned by Design, alongside the GTK UI components it
imports. Core remains independent of Design. Media Player, Theater, and Pulse use
one pinned Design source for nixe-ui and nixe-playback, avoiding both repository
cycles and duplicate crate instances. No playback API or controls were redesigned.

`revision` pins the checkout used for building and packaging. For public libraries,
`dependency_revision` separately pins the supported exported source. CI/packaging
commits do not change that export until an API change is intentionally coordinated.
Release checks validate actual lockfile Git sources against these export pins and
reject stale or duplicate shared-crate sources.

## Exact preparation and development commands

The complete extraction implementation is [tools/prepare-migration.py](tools/prepare-migration.py).
It refuses an existing destination or a changed baseline, verifies tracked source,
creates a full-ref bundle, filters fresh clones, compares baseline file bytes, pins
local Git dependencies, retains lock versions, and commits standalone adaptations.
No remote is configured after filtering. Git-filter-repo 2.47.0 was installed using
`uv tool install git-filter-repo`.

Rehearse in a NEW directory, from the reviewed source baseline:

```bash
cd /home/ken/Projects/nixe
python3 tools/prepare-migration.py \
  --destination /home/ken/Projects/nixe-migration-rehearsal
```

The script's underlying extraction starts with:

```bash
git bundle create /NEW/DEST/nixe-before.bundle --all
git bundle verify /NEW/DEST/nixe-before.bundle
git clone --no-local --single-branch --no-tags --branch main \
  /home/ken/Projects/nixe /NEW/DEST/nixe-core
git -C /NEW/DEST/nixe-core filter-repo \
  --path Cargo.toml --path Cargo.lock --path LICENSE --path rustfmt.toml \
  --path crates/nixe-core/ --path crates/nixe-accounts/ \
  --path crates/nixe-sync/ --path docs/online-accounts/
```

Use the script rather than improvising subsequent filters. Archive's earlier
standalone branch ends at `4d24026`; its five ancestral commits use root-level
src/data. The script renames those paths only in that ancestry, avoiding unrelated
applications' root-level source. Both those commits and the Archive release tag are
retained. Earlier source bytes, authorship, and timestamps were verified through
the commit map. Generic subdirectory filtering alone would lose that history.

Other future app splits must trace their own import/rename chains. Filtering does
not follow renames automatically. Core/Design retain history under their selected
paths; full provenance before copy-based shared-code extraction remains available
in the original repository/bundle. Commit IDs change and rewritten signatures
cannot remain valid. Preserve commit maps and relevant tags; omit unrelated tags.

The implemented developer interfaces are:

```bash
bin/nixe dev setup
bin/nixe dev status
bin/nixe dev build archive
bin/nixe dev test archive
bin/nixe dev test all
bin/nixe release check --structure-only
bin/nixe release check
```

suite.toml records repository revisions, target mappings, versions, historical
supported releases, packages, prerequisite commands, and compatibility contracts.
Ignored .nixe-local.json maps this machine's prepared checkouts. Set NIXE_DEV_HOME
for published clone locations or NIXE_SUITE_MANIFEST for another manifest. Setup
never resets existing checkouts. Build/test reject revision drift. `all` is explicit
and excludes Assistant; request it by name. Native Pulse prerequisites remain
explicit. No command publishes a release.

A normal release check deliberately fails while the suite has unpublished repos,
local file:// dependencies, missing artifacts, or uncommitted changes.
Structure-only validation checks local wiring and shared dependency pins without
claiming publication readiness. `nixe release notes APP` generates notes from the
previous application tag, scoped to the app/domain source.

## Ordered rollout and release strategy

1. Local Core, Design, and all 23 application repositories are prepared. Review
   their receipts; the original monorepo remains a reversible fallback.
2. Approval for all 25 public source repositories is recorded in publication.json.
   New repositories outside that set need separate approval; no force/mirror pushes.
3. Publish Core, Design, Passwords, and Glimpse before the remaining applications.
   Convert local URLs, update lockfiles without refreshing registry versions,
   validate, commit, and publish each consumer. Record checkout and export SHAs.
4. Enable hosted checks only after remote sources resolve. Pin toolchains, action
   commits, container digests, and an Arch package snapshot before release builds.
5. Validate Archive artifacts and route only Archive installation through the new
   repository. Keep the umbrella URL, old assets, rollback path, and current Hyprland
   integration. Extracted applications retain the original MIME defaults, helper, plugin,
   native-library, and legacy migration logic. Standalone installers are scoped
   to their owning app and leave the installed suite CLI in place.
6. Separation of simpler applications, Office/Photos, Weather, and Git is complete.
   Preserve native/system runtime dependencies and packaging contracts during release cutover.
7. Separation of account consumers, GOA helper, Passwords/Glimpse, News/Capture/Pulse
   plugins, playback/media apps, Settings/extensions, and Assistant is complete.
   Playback ownership is resolved in Design; live integrations still need release validation.
8. Release shared API changes dependency-first and test affected consumers before
   changing supported suite pins. Remove old monorepo source only through later
   reviewed normal commits; keep all history and compatibility URLs.

Published repos contain pull-request and manual check workflows that refuse local Git URLs.
The umbrella adds targeted CLI safety/compatibility tests and a gated manual
cross-repository build job. Per-app workflows build locked binaries, run scoped
tests, and package resources. They do not download or run inference models. These are transition scaffolding, not a claim
of production reproducibility or complete cross-repository runtime coverage.

Production CI must provide independent locked app builds/tests, affected-consumer
checks, plugin/D-Bus/schema fixtures, package-resource checks, and dependency-pin
validation. Compare repeat builds before claiming bit-for-bit reproducibility.
Publish checksummed architecture-specific artifacts, versioned Design assets,
per-repository generated release notes, and coordinated suite notes. Enable release
publication only after approval and readiness checks. No model downloads or live
provider sessions belong in routine checks.

Common agent guidance is in docs/AGENTS_COMMON.md. Each prepared repository has a
short AGENTS.md with commands, architecture, public boundaries, style requirements,
and essential offline guidance. The original CLAUDE.md files remain available.

## Validation and rollback

Completed pilot checks are recorded in docs/migration/VALIDATION.md. Keep checks
proportional: an independent locked Archive release build, headless foundation
check, account/sync checks, targeted CLI safety tests, source/history comparisons,
and archive/installation-resource verification. Do not launch/restart the app.
Do not run broad suites, inference, model downloads, or live credential tests.

Main risks are installer layout assumptions; historical root-level import paths;
GTK/system-library requirements; GOA backend availability/stub behavior; native
TDLib/calls packaging; database/plugin contracts; and Core/Design/playback source
coordination. GOA live-provider validation and full suite runtime validation remain
separate future work.

Rollback the local pilot by leaving the prepared directories unused; the source
workspace and original install routes remain functional. Reinstall Archive from the untouched source application using the umbrella
`./install.sh archive` if the independent packaging needs to be rolled back. After any
routing change, revert manifest/installer changes with a normal commit and use
known-good artifacts. Never reset published history or remove user data. A bundle
recovery clone can be made with:

```bash
git clone /home/ken/Projects/nixe-migration-97c1899-reviewed/nixe-before.bundle \
  /NEW/RECOVERY/nixe
```

Pilot review and explicit approval for all 25 public source repositories are complete.
Application release publication and installation-route cutover remain later steps.

## Reproducing the continuation

The import-aware continuation preserves deleted historical paths (including Office's
Qt/QML history), source bytes, authorship, application tags, and extension imports.
It never rewrites or deletes existing repositories. Use a new destination:

```bash
python3 tools/continue-migration.py \
  --destination /NEW/DEST/nixe-apps
python3 tools/configure-standalone-ci.py
python3 tools/validate-migration.py
```

The state file makes continuation resumable. `--reprepare` creates fresh copies in
a new destination while retaining prior attempts. The validation driver performs
one locked release build per app, packages it, and installs without launching;
Git and Store system resources are held until administrator authorization. Assistant
uses its own CUDA build cache and has separate installation/resource checks.

Application packaging uses normalized timestamps/ownership and gzip metadata, records SHA-256,
and retains binaries, icons, launchers, helpers, services, plugins, and native assets.
This improves artifact reproducibility; a pinned Arch snapshot/toolchain/container
and repeat-build comparison are still required before claiming full reproducibility.

Hosted CI runs on pull requests or manual dispatch and refuses local Git URLs.
Source repositories and selected provenance tags are published with ordinary pushes.
No binary GitHub releases or existing organization settings are changed. The existing
umbrella install/update URLs continue to work until independent releases are ready.

## Completed local continuation

All 23 applications passed independent locked release builds and installation.
Git was installed through pacman; Store and Assistant root-owned helpers/policies
were installed after administrator authentication. Existing application/service
processes were not restarted. No inference, model downloads, or live-provider
verification was performed.

The original monorepo application/crate/extension source, Cargo manifests/lockfile,
and STYLE.md still match the baseline. New umbrella files are migration tooling,
manifest/receipts, guidance, and CI. All extracted repositories have independent
entry points, lockfiles, scoped installers, packaging, CI, and agent guidance.

The approved publication converts local Git URLs in dependency order, recomputes
exported revisions and consumer pins, and enables pull-request/manual workflows.
`tools/publish-migration.py` checkpoints every creation/push and backs off on GitHub
creation throttles; rerun it to resume. `tools/record-publication.py` records the
completed set in suite.toml while retaining each binary snapshot's original
`artifact_revision`. Existing umbrella install/update routes remain unchanged.

Remaining release work: pin the build environment, rebuild artifacts against the
published dependency metadata, validate affected integrations, then publish binary
releases and cut over application install routes incrementally. The normal release
check rejects artifacts whose revision predates the published source commit.

The original Assistant feature branches remain in the source repository and full-ref
bundle. Splits track reviewed main history and relevant tags; unmerged branches are
not silently rebased or pushed into the new repositories.

## Approved source publication commands

Publication uses existing history-preserving splits; no force pushes or mirror
pushes are used. The resumable command records created repositories before pushing:

```bash
python3 tools/publish-migration.py
python3 tools/record-publication.py
bin/nixe release check --structure-only
```

For each checkpointed repository the publisher performs the equivalent of:

```bash
gh repo create design-nexus/nixe-APP --public --source /PATH/TO/nixe-APP --remote origin
git -C /PATH/TO/nixe-APP push -u origin main
git -C /PATH/TO/nixe-APP push origin --tags
```

Core is published first, then Design, Passwords, Glimpse, and their consumers.
Cargo resolves GitHub URLs and verifies registry versions remain unchanged before
each consumer commit. Original application tags remain provenance snapshots; use
the pinned main commit for standalone builds. Original umbrella release assets stay
available at their existing URLs. Never rerun preparation over a published checkout.
