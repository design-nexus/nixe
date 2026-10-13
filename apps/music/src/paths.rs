//! Well-known locations. Every path honours the XDG overrides so the whole app
//! can be pointed at a scratch copy of `~/.config` for testing.

pub use nixe_core::paths::*;

use std::path::PathBuf;

/// The library database.
pub fn library_db() -> PathBuf {
    data_dir().join("library.db")
}

/// Downloaded podcast episodes.
pub fn podcasts_dir() -> PathBuf {
    data_dir().join("podcasts")
}

/// Album covers, extracted and scaled once.
pub fn covers_dir() -> PathBuf {
    cache_dir().join("covers")
}

/// The user's music folder (`XDG_MUSIC_DIR`), or `~/Music`.
pub fn music_dir() -> PathBuf {
    let dirs = config_home().join("user-dirs.dirs");
    if let Ok(text) = std::fs::read_to_string(dirs) {
        for line in text.lines() {
            if let Some(v) = line.trim().strip_prefix("XDG_MUSIC_DIR=") {
                let v = v.trim_matches('"').replace("$HOME", &home().to_string_lossy());
                if !v.is_empty() {
                    return PathBuf::from(v);
                }
            }
        }
    }
    home().join("Music")
}


/// The play queue and position, so playback can resume.
pub fn state_file() -> PathBuf {
    data_dir().join("state.json")
}
