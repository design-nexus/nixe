# Common Nyx development guidance

- Preserve existing application display names, executable/package names, application IDs, XDG paths, and stored data formats.
- Consume pinned public shared crates; never depend on another application's private implementation.
- Canonical STYLE.md and GTK components belong to nyx-design. Reuse its widgets, icons, CSS tokens, layouts, and shortcuts. Preserve live Omarchy theme following. Media Player is the reference for shared video playback controls.
- Keep checks targeted. Do not run broad suites, fetch models, or run inference for routine changes.
- Install application updates, including launcher and icon, without opening or restarting applications.
- Coordinate public API changes through suite.toml and affected consumers. Preserve existing D-Bus and plugin protocols unless a separately versioned migration is explicitly approved.
- Keep repository AGENTS.md files concise, with local commands and a pinned copy of these essential rules.
- Never force-push, delete history, or publish a new GitHub repository without explicit approval.
