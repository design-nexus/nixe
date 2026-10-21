# Suite releases

Applications release independently from their owning repositories. Core and Design
publish versioned source/assets; shared Cargo dependencies use immutable public
Git revisions. Cargo.lock preserves registry versions. The suite manifest records
supported checkout commits, immutable release-source commits, shared API export commits, release tags, build features,
asset paths and SHA-256 checksums. A checkout/CI-only commit can differ from its
public API export when the exported Rust code is unchanged. Checkout commits can
also advance past release_revision for CI-only fixes. Release checks reject runtime,
Cargo, installer or asset changes until corresponding artifacts are rebuilt. Source
installation always verifies the immutable release_revision rather than a newer CI commit.

For an application release, commit the source, run `python3 tools/package.py`, then
`python3 tools/release.py --tag vVERSION --publish` in its repository. The manual
release workflow performs locked builds, scoped existing tests, packaging, notes,
and publication using the same scripts. Existing releases are never overwritten.
Publish shared APIs before consumers, update every affected lockfile/pin, and run
suite compatibility checks before merging coordinated release pins.

Every binary release includes build-info.json, CHANGELOG.md, SHA256SUMS and its
archive. Git also supplies an Arch package; Pulse includes its native calling
library/notices; Assistant records CUDA features and bundles its provider libraries.
Inference models are separate runtime downloads, never release/test dependencies.
The installer uses source builds on unsupported binary architectures and for
Assistant on machines without the CUDA runtime required by its binary release.

The container digest, checkout-action commit, Rust version and immutable Arch Linux
Archive snapshot are recorded in build-environment.json. CI uses that environment.
The pinned snapshot supplies Rust 1.99.1. Initial local binaries were built with
Rust 1.99.0 and record that actual compiler in build-info.json. The CI version guard
was corrected without replacing those published binaries. Tar metadata, archive ordering and gzip headers are normalized; Git's package
build date is fixed to the source epoch. Binary bit-for-bit reproducibility across
hosts has not been demonstrated and is not claimed.

`bin/nixe release check` verifies source pins, duplicate/shared crate identities,
release artifact revisions and checksums. Pull requests affecting suite tooling or
manifest run compatibility checks across the repositories. Full cross-repository
compilation can be dispatched through the umbrella integration workflow. The
coordinated release workflow downloads and checks every supported standalone asset
before publishing a suite manifest; locally use `python3 tools/publish-suite.py
--download-assets --tag suite-vVERSION --publish`.

`nixe install APP` and `nixe update` install the supported independent releases,
verify archive hashes, preserve application IDs/data and leave processes alone.
`NIXE_BUILD=1` selects source builds. To roll back routing, use
`NIXE_LEGACY=1 ./install.sh APP` from the frozen umbrella workspace, or pin an earlier
known-good release in suite.toml and its corresponding artifact checksum. Keep old
GitHub releases and history. Never roll back or replace user databases.
