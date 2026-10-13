//! Well-known locations. Every path honours the XDG overrides so the whole app
//! can be pointed at a scratch copy of `~/.config` for testing.

pub use nixe_core::paths::*;

use std::path::PathBuf;

pub fn library_db() -> PathBuf {
    data_dir().join("library.db")
}

pub fn signatures_dir() -> PathBuf {
    data_dir().join("signatures")
}

/// Page-one pictures for the library.
pub fn covers_dir() -> PathBuf {
    cache_dir().join("covers")
}

/// Working copies of open documents (one folder per open file).
pub fn work_dir() -> PathBuf {
    cache_dir().join("work")
}

pub fn documents_dir() -> PathBuf {
    let dirs = config_home().join("user-dirs.dirs");
    if let Ok(text) = std::fs::read_to_string(dirs) {
        for line in text.lines() {
            if let Some(v) = line.trim().strip_prefix("XDG_DOCUMENTS_DIR=") {
                let v = v.trim_matches('"').replace("$HOME", &home().to_string_lossy());
                if !v.is_empty() {
                    return PathBuf::from(v);
                }
            }
        }
    }
    home().join("Documents")
}

