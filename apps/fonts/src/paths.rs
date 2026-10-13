//! Well-known locations. Every path honours the XDG overrides so the whole app
//! can be pointed at a scratch copy of `~/.config` for testing.

pub use nixe_core::paths::*;

use std::path::PathBuf;

/// What this app installed, and from where.
pub fn installed_file() -> PathBuf {
    state_home().join("nexus-fonts/installed.toml")
}

/// The user's font folder.
pub fn user_fonts_dir() -> PathBuf {
    data_home().join("fonts")
}

/// Where installed fonts go: `~/.local/share/fonts/nexus-fonts`.
pub fn fonts_dir() -> PathBuf {
    user_fonts_dir().join("nexus-fonts")
}

/// One font file per family, for previews.
pub fn preview_dir() -> PathBuf {
    cache_dir().join("preview")
}

