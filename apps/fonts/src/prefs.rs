//! This app's own preferences (`~/.config/nexus-fonts/settings.toml`).

pub use nixe_theme::ThemeMode;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Prefs {
    pub mode: ThemeMode,
    pub theme: String,
    pub reduce_motion: bool,
    /// The sidebar shows only icons, whatever the window width.
    pub sidebar_collapsed: bool,
    pub glow: bool,
    pub last_section: String,
    /// Which Google Fonts files to install: static, variable or both.
    pub google_files: String,
    /// Which Nerd Font variants to keep: all, mono or regular (regular and Propo).
    pub nerd_variants: String,
    /// Run fc-cache after installing or removing.
    pub refresh_cache: bool,
    /// The preview's sample text.
    pub sample: String,
    /// The preview's size in points.
    pub preview_size: f64,
    /// How the Google Fonts table is sorted: popular, trending, name or newest.
    pub google_sort: String,
    /// Unix time the catalogs were last fetched.
    pub catalog_fetched: i64,
}

pub const DEFAULT_SAMPLE: &str = "The quick brown fox jumps over the lazy dog";

impl Default for Prefs {
    fn default() -> Self {
        Self {
            mode: ThemeMode::Omarchy,
            theme: "tokyo-night".into(),
            reduce_motion: false,
            sidebar_collapsed: false,
            glow: true,
            last_section: "google".into(),
            google_files: "static".into(),
            nerd_variants: "all".into(),
            refresh_cache: true,
            sample: DEFAULT_SAMPLE.into(),
            preview_size: 32.0,
            google_sort: "popular".into(),
            catalog_fetched: 0,
        }
    }
}

nixe_core::prefs_store!(Prefs);
