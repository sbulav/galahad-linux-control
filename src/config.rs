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

impl From<Rgb> for image::Rgb<u8> {
    fn from(rgb: Rgb) -> Self {
        image::Rgb([rgb.0, rgb.1, rgb.2])
    }
}

/// Colours used by the default (non-preset) display.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Colors {
    /// Clock text.
    pub time: Rgb,
    /// Date text.
    pub date: Rgb,
    /// CPU temperature text.
    pub cpu_temp: Rgb,
    /// CPU usage text.
    pub cpu_usage: Rgb,
    /// Translucent panel drawn over a background image.
    pub overlay: Rgb,
    /// Solid fill when there is no background image.
    pub background: Rgb,
    /// Inner 400x400 rectangle drawn when there is no background image.
    pub panel: Rgb,
}

pub const DEFAULT_COLORS: Colors = Colors {
    time: Rgb(0, 255, 200),
    date: Rgb(120, 120, 120),
    cpu_temp: Rgb(0, 200, 255),
    cpu_usage: Rgb(255, 160, 0),
    overlay: Rgb(0, 0, 0),
    background: Rgb(30, 30, 30),
    panel: Rgb(10, 10, 10),
};

impl Default for Colors {
    fn default() -> Self {
        DEFAULT_COLORS
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
    pub colors: Colors,
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
    preset: Option<String>,
    colors: Option<FileColors>,
}

#[derive(Debug, Deserialize, Default)]
struct FileColors {
    time: Option<String>,
    date: Option<String>,
    cpu_temp: Option<String>,
    cpu_usage: Option<String>,
    overlay: Option<String>,
    background: Option<String>,
    panel: Option<String>,
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

/// The config file to use: `--config` if given (even if it does not exist yet),
/// otherwise the first existing default path.
pub fn resolve_config_path(args: &Args) -> Option<PathBuf> {
    args.config.clone().or_else(find_config_file)
}

/// Load settings from `path` merged under the CLI arguments. Never fatal: a
/// missing or unparsable file prints a warning and falls back to defaults.
pub fn load_settings_from(args: &Args, path: Option<&Path>) -> Settings {
    let file_config = match path {
        Some(path) if path.exists() => load_config(path).unwrap_or_else(|err| {
            eprintln!(
                "Warning: Failed to load config file {}: {err:#}",
                path.display()
            );
            FileConfig::default()
        }),
        Some(path) => {
            eprintln!(
                "Warning: Config file {} does not exist; using defaults",
                path.display()
            );
            FileConfig::default()
        }
        None => FileConfig::default(),
    };

    merge(args, file_config)
}

pub fn load_settings(args: &Args) -> Settings {
    load_settings_from(args, resolve_config_path(args).as_deref())
}

/// The pump RGB colour actually applied: presets force their own colour.
pub fn effective_rgb(settings: &Settings) -> Rgb {
    match settings.preset {
        Some(PresetMode::Matrix) => Rgb(0, 255, 0),
        Some(PresetMode::Heartbeat) => Rgb(255, 0, 0),
        None => settings.rgb,
    }
}

fn load_config(path: &Path) -> Result<FileConfig> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("failed to read config file {}", path.display()))?;
    let config: FileConfig = toml::from_str(&content)
        .with_context(|| format!("failed to parse TOML config {}", path.display()))?;
    Ok(config.normalized())
}

/// Parse an optional config value, warning (instead of silently ignoring) on failure.
fn parse_key<T>(
    key: &str,
    value: Option<&str>,
    parse: impl Fn(&str) -> Result<T, String>,
) -> Option<T> {
    let value = value?;
    match parse(value) {
        Ok(parsed) => Some(parsed),
        Err(err) => {
            eprintln!("Warning: ignoring config key {key} = {value:?}: {err}");
            None
        }
    }
}

fn merge_colors(colors: Option<FileColors>) -> Colors {
    let file = colors.unwrap_or_default();
    let d = DEFAULT_COLORS;
    let pick = |key: &str, value: &Option<String>, default: Rgb| {
        parse_key(key, value.as_deref(), parse_color).unwrap_or(default)
    };
    Colors {
        time: pick("colors.time", &file.time, d.time),
        date: pick("colors.date", &file.date, d.date),
        cpu_temp: pick("colors.cpu_temp", &file.cpu_temp, d.cpu_temp),
        cpu_usage: pick("colors.cpu_usage", &file.cpu_usage, d.cpu_usage),
        overlay: pick("colors.overlay", &file.overlay, d.overlay),
        background: pick("colors.background", &file.background, d.background),
        panel: pick("colors.panel", &file.panel, d.panel),
    }
}

fn merge(args: &Args, config: FileConfig) -> Settings {
    let config_rgb = parse_key("rgb", config.rgb.as_deref(), parse_color);
    let config_bg_mode = parse_key("bg_mode", config.bg_mode.as_deref(), str::parse);
    let config_preset = parse_key("preset", config.preset.as_deref(), str::parse);
    let config_bg = config.bg.or(config.background).map(expand_home);

    Settings {
        rgb: args.rgb.or(config_rgb).unwrap_or(DEFAULT_RGB),
        fps: args.fps.or(config.fps).unwrap_or(DEFAULT_FPS),
        bg: args.bg.clone().or(config_bg),
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
        preset: args.preset.or(config_preset),
        colors: merge_colors(config.colors),
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

    fn parse(toml: &str) -> FileConfig {
        toml::from_str::<FileConfig>(toml).unwrap().normalized()
    }

    #[test]
    fn preserves_default_settings() {
        let settings = merge(&Args::default(), FileConfig::default());
        assert_eq!(settings.rgb, DEFAULT_RGB);
        assert_eq!(settings.fps, DEFAULT_FPS);
        assert_eq!(settings.bg_mode, ScalingMode::Fill);
        assert!(settings.show_overlay);
        assert_eq!(settings.preset, None);
        assert_eq!(settings.colors, Colors::default());
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
        let settings = merge(&args, config);
        assert_eq!(settings.rgb, Rgb(1, 2, 3));
        assert_eq!(settings.fps, 20.0);
    }

    #[test]
    fn config_preset_is_used_when_cli_has_none() {
        let settings = merge(&Args::default(), parse(r#"preset = "Heartbeat""#));
        assert_eq!(settings.preset, Some(PresetMode::Heartbeat));
    }

    #[test]
    fn cli_preset_overrides_config() {
        let args = Args {
            preset: Some(PresetMode::Matrix),
            ..Args::default()
        };
        let settings = merge(&args, parse(r#"preset = "heartbeat""#));
        assert_eq!(settings.preset, Some(PresetMode::Matrix));
    }

    #[test]
    fn invalid_values_fall_back_to_defaults() {
        let settings = merge(
            &Args::default(),
            parse(
                r#"
                rgb = "nope"
                bg_mode = "zoom"
                preset = "disco"
                "#,
            ),
        );
        assert_eq!(settings.rgb, DEFAULT_RGB);
        assert_eq!(settings.bg_mode, DEFAULT_BG_MODE);
        assert_eq!(settings.preset, None);
    }

    #[test]
    fn colors_table_overrides_defaults() {
        let config = parse(
            r##"
            [colors]
            time = "#ff0000"
            panel = "0,0,64"
            "##,
        );
        let settings = merge(&Args::default(), config);
        assert_eq!(settings.colors.time, Rgb(255, 0, 0));
        assert_eq!(settings.colors.panel, Rgb(0, 0, 64));
        assert_eq!(settings.colors.date, DEFAULT_COLORS.date);
        assert_eq!(settings.colors.background, DEFAULT_COLORS.background);
    }

    #[test]
    fn nested_gaii_control_section_still_works() {
        let config = parse(
            r##"
            [gaii-control]
            rgb = "blue"
            fps = 12.5
            bg_mode = "fit"
            preset = "matrix"

            [gaii-control.colors]
            date = "#010203"
            "##,
        );
        let settings = merge(&Args::default(), config);
        assert_eq!(settings.rgb, Rgb(0, 0, 255));
        assert_eq!(settings.fps, 12.5);
        assert_eq!(settings.bg_mode, ScalingMode::Fit);
        assert_eq!(settings.preset, Some(PresetMode::Matrix));
        assert_eq!(settings.colors.date, Rgb(1, 2, 3));
    }

    #[test]
    fn effective_rgb_follows_preset() {
        let mut settings = merge(
            &Args {
                rgb: Some(Rgb(9, 8, 7)),
                ..Args::default()
            },
            FileConfig::default(),
        );
        assert_eq!(effective_rgb(&settings), Rgb(9, 8, 7));
        settings.preset = Some(PresetMode::Matrix);
        assert_eq!(effective_rgb(&settings), Rgb(0, 255, 0));
        settings.preset = Some(PresetMode::Heartbeat);
        assert_eq!(effective_rgb(&settings), Rgb(255, 0, 0));
    }

    #[test]
    fn missing_explicit_config_is_not_fatal() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("absent.toml");
        let args = Args {
            config: Some(path.clone()),
            ..Args::default()
        };
        assert_eq!(resolve_config_path(&args), Some(path.clone()));
        let settings = load_settings_from(&args, Some(&path));
        assert_eq!(settings.rgb, DEFAULT_RGB);
    }

    #[test]
    fn loads_explicit_config_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("glc.toml");
        std::fs::write(&path, "fps = 7.0\n[colors]\ncpu_temp = \"white\"\n").unwrap();
        let args = Args {
            config: Some(path.clone()),
            ..Args::default()
        };
        let settings = load_settings(&args);
        assert_eq!(settings.fps, 7.0);
        assert_eq!(settings.colors.cpu_temp, Rgb(255, 255, 255));
    }
}
