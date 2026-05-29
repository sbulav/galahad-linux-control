use crate::cli::{parse_color, Args, PresetMode, ScalingMode};
use anyhow::{Context, Result};
use serde::Deserialize;
use std::path::{Path, PathBuf};

pub const VENDOR_ID: u16 = 0x0416;
pub const PRODUCT_ID: u16 = 0x7395;
pub const INTERFACE_CONTROL: u8 = 1;

pub const LCD_WIDTH: u32 = 480;
pub const LCD_HEIGHT: u32 = 480;
pub const DEFAULT_FPS: f32 = 5.0;
pub const DEFAULT_RGB: Rgb = Rgb(0, 255, 200);
pub const DEFAULT_BG_MODE: ScalingMode = ScalingMode::Fill;
pub const DEFAULT_OVERLAY_OPACITY: u8 = 180;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Rgb(pub u8, pub u8, pub u8);

impl std::fmt::Display for Rgb {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "({}, {}, {})", self.0, self.1, self.2)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Settings {
    pub rgb: Rgb,
    pub fps: f32,
    pub bg: Option<PathBuf>,
    pub bg_mode: ScalingMode,
    pub show_overlay: bool,
    pub overlay_opacity: u8,
    pub preset: Option<PresetMode>,
}

#[derive(Debug, Deserialize, Default)]
struct FileConfig {
    #[serde(rename = "gaii-control")]
    gaii_control: Option<Box<FileConfig>>,
    rgb: Option<String>,
    fps: Option<f32>,
    bg: Option<String>,
    background: Option<String>,
    bg_mode: Option<String>,
    overlay: Option<bool>,
    overlay_opacity: Option<u8>,
}

impl FileConfig {
    fn normalized(self) -> Self {
        if let Some(section) = self.gaii_control {
            *section
        } else {
            self
        }
    }
}

pub fn default_config_paths() -> Vec<PathBuf> {
    let home = std::env::var_os("HOME").map(PathBuf::from);
    let mut paths = Vec::new();
    if let Some(home) = &home {
        paths.push(home.join(".config/gaii-control/config.toml"));
        paths.push(home.join("gaii-control.toml"));
    }
    paths.push(PathBuf::from("./gaii-control.toml"));
    paths
}

pub fn find_config_file() -> Option<PathBuf> {
    default_config_paths()
        .into_iter()
        .find(|path| path.exists())
}

pub fn load_settings(args: Args) -> Result<Settings> {
    let file_config = match find_config_file() {
        Some(path) => load_config(&path).unwrap_or_else(|err| {
            eprintln!(
                "Warning: Failed to load config file {}: {err}",
                path.display()
            );
            FileConfig::default()
        }),
        None => FileConfig::default(),
    };

    Ok(merge(args, file_config))
}

fn load_config(path: &Path) -> Result<FileConfig> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("failed to read config file {}", path.display()))?;
    let config: FileConfig = toml::from_str(&content)
        .with_context(|| format!("failed to parse TOML config {}", path.display()))?;
    Ok(config.normalized())
}

fn merge(args: Args, config: FileConfig) -> Settings {
    let config_rgb = config.rgb.as_deref().and_then(|s| parse_color(s).ok());
    let config_bg_mode = config
        .bg_mode
        .as_deref()
        .and_then(|mode| mode.parse::<ScalingMode>().ok());
    let config_bg = config.bg.or(config.background).map(expand_home);

    Settings {
        rgb: args.rgb.or(config_rgb).unwrap_or(DEFAULT_RGB),
        fps: args.fps.or(config.fps).unwrap_or(DEFAULT_FPS),
        bg: args.bg.or(config_bg),
        bg_mode: args.bg_mode.or(config_bg_mode).unwrap_or(DEFAULT_BG_MODE),
        show_overlay: if args.no_overlay {
            false
        } else {
            config.overlay.unwrap_or(true)
        },
        overlay_opacity: args
            .overlay_opacity
            .or(config.overlay_opacity)
            .unwrap_or(DEFAULT_OVERLAY_OPACITY),
        preset: args.preset,
    }
}

fn expand_home(path: String) -> PathBuf {
    if let Some(stripped) = path.strip_prefix("~/") {
        if let Some(home) = std::env::var_os("HOME") {
            return PathBuf::from(home).join(stripped);
        }
    }
    PathBuf::from(path)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn preserves_default_settings() {
        let settings = merge(Args::default(), FileConfig::default());
        assert_eq!(settings.rgb, DEFAULT_RGB);
        assert_eq!(settings.fps, DEFAULT_FPS);
        assert_eq!(settings.bg_mode, ScalingMode::Fill);
        assert!(settings.show_overlay);
    }

    #[test]
    fn cli_overrides_config() {
        let args = Args {
            rgb: Some(Rgb(1, 2, 3)),
            fps: Some(20.0),
            ..Args::default()
        };
        let config = FileConfig {
            rgb: Some("red".into()),
            fps: Some(1.0),
            ..FileConfig::default()
        };
        let settings = merge(args, config);
        assert_eq!(settings.rgb, Rgb(1, 2, 3));
        assert_eq!(settings.fps, 20.0);
    }
}
