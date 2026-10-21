# Nixe umbrella and transition workspace

This repository coordinates the independently released suite. App implementations
live in their own nixe-<app> repositories; shared APIs/assets live in nixe-core and
nixe-design. Use suite.toml and `bin/nixe dev setup` to locate owning checkouts.
The retained apps/, crates/, extensions/, and root Cargo files are a frozen rollback
workspace. Do not implement new application changes in those legacy copies.

Migration baseline and boundaries: MULTIREPO_MIGRATION.md.
Suite source of truth: suite.toml. Local checkout overrides: ignored .nixe-local.json. All 23 application splits are
independent; see suite.toml for supported immutable commits and
docs/migration/repositories.json for active local locations.
Common agent rules: docs/AGENTS_COMMON.md. Canonical shared style and widgets
are maintained in design-nexus/nixe-design. STYLE.md here is the preserved baseline.

Commands: `bin/nixe dev status`, `bin/nixe dev build archive`,
`bin/nixe release check`, `bin/nixe release notes APP`.
Install/update commands consume versioned standalone releases and verify manifest
checksums. `NIXE_BUILD=1` builds the owning source repo; `NIXE_LEGACY=1` is rollback.
Run only essential checks for changed packages. Never download models or run
inference for routine verification. Keep identities, application data, and existing
integrations stable. Use public pinned dependencies across repository boundaries.
Install updates without opening/restarting applications. The 25 source repositories
have publication approval; new remote repositories still require explicit approval.
