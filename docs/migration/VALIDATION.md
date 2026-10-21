# Local pilot validation

Baseline: 97c1899499e52a42f6eaddca188aac4eca32b96e.
Historical pilot preparation: `nixe-migration-97c1899-reviewed`, now preserved in
`/home/ken/Archives/nixe-migration-2026-10-21/`. Active repositories are siblings
of the umbrella in `/home/ken/Projects/`.

- Full source-ref bundle verified.
- Selected baseline files compared byte-for-byte before standalone adaptations.
- Archive's five pre-import commits retain main source bytes, author/committer names,
  and timestamps; archive-v0.1.0 retained. Commit maps saved alongside the bundle.
- Archive independently built with `cargo build --release --locked -p nixe-archive`.
  Shared target cache was reused; dependency sources are pinned Git repositories,
  not sibling path dependencies.
- Extracted foundation checked with its default GTK feature disabled.
- Extracted accounts and sync crates checked with their lockfile.
- Five targeted CLI tests passed: real boundaries, unknown application diagnostics,
  preserving existing checkouts, rejecting floating revisions, rejecting stale shared-library revisions.
- Suite local structure and shell syntax checks passed.
- Registry package versions retained from original Cargo.lock.

No GUI, model inference, live provider, or whole-suite runtime tests were performed.
These initial pilot checks preceded the complete separation and publication recorded below.

- Archive release archive inspected: executable, desktop launcher, icon, and license.
- Installed Archive binary, launcher, and icon match prepared build/resources.
- Design assets archive generated; both artifacts have SHA-256 values in suite.toml.
- Full release readiness check correctly blocks unpublished/local sources and apps
  still in the monorepo. Structure-only validation passes.

## Completed application separation

- All 23 applications have independent local repositories and locked release builds.
- All user binaries/resources are installed, including the pacman-managed Git
  package and privileged Store/Assistant helpers and policies.
- No application or service was started/restarted by the migration installers.
- Original application/crate/extension source and root Cargo inputs remain unchanged.
- Original registry dependency versions were retained in every application lockfile.
- Import-aware filtering retains standalone application histories, including deleted
  Qt/QML paths and Settings' extension repository ancestry. Relevant tags retained.
- Per-app source/binary build receipts, SHA-256 artifacts, and changelogs are in
  application-validation.json, repositories.json, suite.toml, and each repo's dist/.
- Shared export revisions and duplicate crate identities are checked against lockfiles.
- Independent CI checks pull requests/manual dispatch and rejects local dependency sources.
- Design asset archive metadata was normalized; repeated output hashes match.

Live GOA/EDS/provider behavior, GUI interaction, inference, and complete toolchain/
container reproducibility were not tested. Source publication is recorded separately
in publication.json; no new binary releases were created.

Final resource check: every packaged Rust executable matches its installed user or
system binary. All prepared repositories are clean. Structure/shared-pin checks
pass. Binary snapshots retain their pre-publication revisions; release checks reject
using them as artifacts for the newer published source metadata.

## Source publication verification

- Explicit user approval covers 25 new public repositories (Core, Design, 23 apps).
- Publication checkpoints record created/pushed repositories and immutable commits.
- Each converted workspace resolves its GitHub dependencies with Cargo metadata;
  registry package versions are checked against its pre-conversion lockfile.
- Archive passes `cargo check --locked -p nixe-archive` using the published Core
  and Design sources. No Rust implementation changes were made during publication.
- Five targeted CLI tests and umbrella shell syntax checks pass.
- Prior binary artifacts/build/install receipts are preserved at their original
  revisions. No GitHub binary releases are uploaded by source publication.

## Final independent releases and installation

- All 23 applications passed locked release builds against the published Core,
  Design, Passwords protocol and Glimpse SDK export commits.
- Core and Design publish v0.1.0 source/assets; all apps publish v0.1.0 archives,
  changelogs, build information and SHA256SUMS. Git also publishes its Arch package.
- CI pins a container digest, checkout action commit and dated Arch package snapshot.
- All app binaries, launchers/icons, companion plugins and native runtime files are
  installed. Git's pacman package and Store/Assistant root helpers match this build.
- Installed executable hashes match the release builds; linked libraries resolve.
- The umbrella's Archive download/checksum/extract/install path passed against its
  public GitHub release. Applications and services were not opened/restarted.
- Source rollback remains in the original workspace and preserved bundles. The
  default installer/update route consumes manifest-pinned independent releases.
- Existing five CLI checks, shell syntax and cross-repository structure checks pass.
  Live GUI/provider/inference behavior and cross-host bitwise equality are untested.
