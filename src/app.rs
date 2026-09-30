//! Runtime display state and hot-reload bookkeeping, kept free of USB access
//! so it can be unit-tested without the pump.

use crate::cli::{PresetMode, ScalingMode};
use crate::config::{effective_rgb, Rgb, Settings};
use crate::metrics::CpuMeter;
use crate::presets::{HeartbeatPreset, MatrixPreset, Preset};
use crate::render::{create_frame, load_background, Fonts};
use image::RgbImage;
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

/// How often the config file and background are re-stat'ed.
pub const RELOAD_INTERVAL: Duration = Duration::from_secs(1);

/// Modification time of `path` (following symlinks), `None` when missing.
pub fn file_mtime(path: &Path) -> Option<SystemTime> {
    std::fs::metadata(path).and_then(|m| m.modified()).ok()
}

/// Identity of a background file: its resolved target and that target's mtime.
/// Changes when a symlink is re-pointed or the target is rewritten.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct BgIdentity {
    pub target: Option<PathBuf>,
    pub mtime: Option<SystemTime>,
}

impl BgIdentity {
    pub fn of(path: Option<&Path>) -> Self {
        let Some(path) = path else {
            return Self::default();
        };
        let target = std::fs::canonicalize(path).ok();
        let mtime = target.as_deref().and_then(file_mtime);
        Self { target, mtime }
    }
}

/// Everything that decides which background image is shown.
#[derive(Debug, Clone, PartialEq)]
struct BgKey {
    path: Option<PathBuf>,
    mode: ScalingMode,
    identity: BgIdentity,
    wanted: bool,
}

impl BgKey {
    fn of(settings: &Settings) -> Self {
        Self {
            path: settings.bg.clone(),
            mode: settings.bg_mode,
            identity: BgIdentity::of(settings.bg.as_deref()),
            wanted: settings.preset.is_none(),
        }
    }
}

/// What a reload changed. `rgb` is set when the pump colour must be re-sent.
#[derive(Debug, Default, PartialEq)]
pub struct Reload {
    pub rgb: Option<Rgb>,
    pub changes: Vec<String>,
}

impl Reload {
    pub fn summary(&self) -> String {
        if self.changes.is_empty() {
            "no effective changes".into()
        } else {
            self.changes.join(", ")
        }
    }
}

pub struct Display {
    settings: Settings,
    bg: Option<RgbImage>,
    bg_key: BgKey,
    preset: Option<Box<dyn Preset>>,
}

impl Display {
    pub fn new(settings: Settings) -> Self {
        let bg_key = BgKey::of(&settings);
        Self {
            bg: build_background(&settings),
            preset: build_preset(&settings),
            bg_key,
            settings,
        }
    }

    pub fn settings(&self) -> &Settings {
        &self.settings
    }

    pub fn frame_delay(&self) -> Duration {
        Duration::from_secs_f32(1.0 / self.settings.fps.max(0.1))
    }

    /// Identity of the background as currently configured on disk; compare it
    /// with [`Display::loaded_bg_identity`] to detect a re-pointed symlink.
    pub fn current_bg_identity(&self) -> BgIdentity {
        BgIdentity::of(self.settings.bg.as_deref())
    }

    pub fn loaded_bg_identity(&self) -> &BgIdentity {
        &self.bg_key.identity
    }

    /// Switch to `new` settings, rebuilding only what changed.
    pub fn apply(&mut self, new: Settings) -> Reload {
        let mut reload = Reload::default();
        let old = std::mem::replace(&mut self.settings, new);
        let new = &self.settings;

        let rgb = effective_rgb(new);
        if rgb != effective_rgb(&old) {
            reload.rgb = Some(rgb);
            reload.changes.push(format!("rgb {rgb}"));
        }

        let heartbeat_fps_changed = new.preset == Some(PresetMode::Heartbeat) && new.fps != old.fps;
        if new.preset != old.preset || heartbeat_fps_changed {
            self.preset = build_preset(new);
            reload.changes.push(format!(
                "preset {}",
                new.preset.map_or_else(|| "none".into(), |p| p.to_string())
            ));
        }

        if new.fps != old.fps {
            reload.changes.push(format!("fps {}", new.fps));
        }

        let bg_key = BgKey::of(new);
        if bg_key != self.bg_key {
            self.bg = build_background(new);
            self.bg_key = bg_key;
            reload
                .changes
                .push(format!("background {}", describe_bg(new)));
        }

        if new.show_overlay != old.show_overlay || new.overlay_opacity != old.overlay_opacity {
            reload.changes.push(format!(
                "overlay {} (opacity {})",
                new.show_overlay, new.overlay_opacity
            ));
        }

        if new.colors != old.colors {
            reload.changes.push("colors".into());
        }

        reload
    }

    pub fn render(&mut self, fonts: &Fonts, cpu: &mut CpuMeter) -> RgbImage {
        match self.preset.as_mut() {
            Some(preset) => preset.render(fonts, cpu),
            None => create_frame(
                self.bg.as_ref(),
                self.settings.show_overlay,
                self.settings.overlay_opacity,
                &self.settings.colors,
                fonts,
                cpu,
            ),
        }
    }
}

pub fn describe_bg(settings: &Settings) -> String {
    settings
        .bg
        .as_ref()
        .map(|p| p.display().to_string())
        .unwrap_or_else(|| "solid".into())
}

fn build_background(settings: &Settings) -> Option<RgbImage> {
    if settings.preset.is_some() {
        return None;
    }
    let path = settings.bg.as_ref()?;
    match load_background(path, settings.bg_mode) {
        Ok(image) => Some(image),
        Err(err) => {
            eprintln!("⚠️  Warning: {err:#}; falling back to solid colors");
            None
        }
    }
}

fn build_preset(settings: &Settings) -> Option<Box<dyn Preset>> {
    match settings.preset? {
        PresetMode::Matrix => Some(Box::new(MatrixPreset::new())),
        PresetMode::Heartbeat => Some(Box::new(HeartbeatPreset::new(settings.fps))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cli::Args;
    use crate::config::{load_settings_from, DEFAULT_RGB};

    fn defaults() -> Settings {
        load_settings_from(&Args::default(), None)
    }

    fn write_png(path: &Path, color: [u8; 3]) {
        RgbImage::from_pixel(8, 8, image::Rgb(color))
            .save(path)
            .unwrap();
    }

    #[test]
    fn unchanged_settings_reload_nothing() {
        let mut display = Display::new(defaults());
        let reload = display.apply(defaults());
        assert_eq!(reload, Reload::default());
        assert_eq!(reload.summary(), "no effective changes");
    }

    #[test]
    fn preset_change_resends_rgb_and_drops_background() {
        let dir = tempfile::tempdir().unwrap();
        let bg = dir.path().join("bg.png");
        write_png(&bg, [255, 0, 0]);
        let mut settings = defaults();
        settings.bg = Some(bg);
        let mut display = Display::new(settings.clone());
        assert!(display.bg.is_some());

        settings.preset = Some(PresetMode::Matrix);
        let reload = display.apply(settings.clone());
        assert_eq!(reload.rgb, Some(Rgb(0, 255, 0)));
        assert!(display.preset.is_some());
        assert!(display.bg.is_none());

        settings.preset = None;
        let reload = display.apply(settings);
        assert_eq!(reload.rgb, Some(DEFAULT_RGB));
        assert!(display.preset.is_none());
        assert!(display.bg.is_some());
    }

    #[test]
    fn fps_change_updates_frame_delay() {
        let mut display = Display::new(defaults());
        let mut settings = defaults();
        settings.fps = 4.0;
        let reload = display.apply(settings);
        assert_eq!(reload.rgb, None);
        assert_eq!(reload.changes, vec!["fps 4".to_string()]);
        assert_eq!(display.frame_delay(), Duration::from_millis(250));
    }

    #[cfg(unix)]
    #[test]
    fn repointed_background_symlink_is_detected_and_reloaded() {
        let dir = tempfile::tempdir().unwrap();
        let red = dir.path().join("red.png");
        let blue = dir.path().join("blue.png");
        write_png(&red, [255, 0, 0]);
        write_png(&blue, [0, 0, 255]);
        let link = dir.path().join("current.png");
        std::os::unix::fs::symlink(&red, &link).unwrap();

        let mut settings = defaults();
        settings.bg = Some(link.clone());
        settings.show_overlay = false;
        let mut display = Display::new(settings.clone());
        assert_eq!(display.current_bg_identity(), *display.loaded_bg_identity());

        std::fs::remove_file(&link).unwrap();
        std::os::unix::fs::symlink(&blue, &link).unwrap();
        assert_ne!(display.current_bg_identity(), *display.loaded_bg_identity());

        let reload = display.apply(settings);
        assert!(reload.changes.iter().any(|c| c.starts_with("background")));
        assert_eq!(display.current_bg_identity(), *display.loaded_bg_identity());

        let fonts = Fonts::load();
        let mut cpu = CpuMeter::default();
        let frame = display.render(&fonts, &mut cpu);
        assert_eq!(frame.get_pixel(0, 0), &image::Rgb([0, 0, 255]));
    }

    #[test]
    fn missing_background_is_not_fatal() {
        let mut settings = defaults();
        settings.bg = Some(PathBuf::from("/nonexistent/glc-bg.png"));
        let display = Display::new(settings);
        assert!(display.bg.is_none());
        assert_eq!(display.current_bg_identity(), BgIdentity::default());
    }
}
