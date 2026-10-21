# Nixe umbrella and transition workspace

The existing Cargo workspace remains operational during incremental extraction.
`apps/*` contains application packages; `crates/*` shared and domain crates.
Assistant, extensions, and Glimpse inference have separate build arrangements.

Migration baseline and boundaries: MULTIREPO_MIGRATION.md.
Suite source of truth: suite.toml. Local checkout overrides: ignored .nixe-local.json. All 23 application splits are
independent; see suite.toml for supported immutable commits and
docs/migration/repositories.json for active local locations.
Common agent rules: docs/AGENTS_COMMON.md. Canonical shared style and widgets
are maintained in design-nexus/nixe-design. STYLE.md here is the preserved baseline.

Commands: `bin/nixe dev status`, `bin/nixe dev build archive`,
`bin/nixe release check --structure-only`, `bin/nixe release notes APP`. Legacy install/update commands remain.
Run only essential checks for changed packages. Never download models or run
inference for routine verification. Keep identities, application data, and existing
integrations stable. Use public pinned dependencies across repository boundaries.
Install updates without opening/restarting applications. The 25 source repositories
have publication approval; new remote repositories still require explicit approval.
