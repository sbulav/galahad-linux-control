use crate::config::Rgb;
use clap::{Parser, ValueEnum};
use std::path::PathBuf;
use std::str::FromStr;

#[derive(Debug, Clone, Parser, Default)]
#[command(name = "glc", about = "Lian Li Galahad II LCD control")]
pub struct Args {
    #[arg(
        short = 'c',
        long = "rgb",
        value_parser = parse_color,
        value_name = "COLOR",
        help = "RGB light color: name, hex (#RRGGBB), or r,g,b"
    )]
    pub rgb: Option<Rgb>,

    #[arg(short = 'f', long = "fps", help = "Display refresh rate in FPS")]
    pub fps: Option<f32>,

    #[arg(
        long = "bg",
        alias = "background",
        value_name = "PATH",
        help = "Background image file (PNG, JPG, etc.)"
    )]
    pub bg: Option<PathBuf>,

    #[arg(long = "bg-mode", help = "Background scaling mode")]
    pub bg_mode: Option<ScalingMode>,

    #[arg(long = "no-overlay", help = "Disable time/date/CPU overlay")]
    pub no_overlay: bool,

    #[arg(
        long = "overlay-opacity",
        value_parser = clap::value_parser!(u8).range(0..=255),
        value_name = "0-255",
        help = "Overlay background opacity (0=transparent, 255=solid)"
    )]
    pub overlay_opacity: Option<u8>,

    #[arg(
        short = 'p',
        long = "preset",
        help = "Display preset mode: matrix or heartbeat"
    )]
    pub preset: Option<PresetMode>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum PresetMode {
    Matrix,
    Heartbeat,
}

impl std::fmt::Display for PresetMode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PresetMode::Matrix => write!(f, "matrix"),
            PresetMode::Heartbeat => write!(f, "heartbeat"),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum ScalingMode {
    Stretch,
    Fit,
    Fill,
}

impl FromStr for ScalingMode {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_ascii_lowercase().as_str() {
            "stretch" => Ok(Self::Stretch),
            "fit" => Ok(Self::Fit),
            "fill" => Ok(Self::Fill),
            _ => Err(format!("invalid scaling mode '{s}'")),
        }
    }
}

pub fn parse_color(color: &str) -> Result<Rgb, String> {
    let trimmed = color.trim();
    let lower = trimmed.to_ascii_lowercase();

    if let Some(rgb) = named_color(&lower) {
        return Ok(rgb);
    }

    let hex = trimmed.strip_prefix('#').unwrap_or(trimmed);
    if hex.len() == 6 {
        if let (Ok(r), Ok(g), Ok(b)) = (
            u8::from_str_radix(&hex[0..2], 16),
            u8::from_str_radix(&hex[2..4], 16),
            u8::from_str_radix(&hex[4..6], 16),
        ) {
            return Ok(Rgb(r, g, b));
        }
    }

    if trimmed.contains(',') {
        let parts: Result<Vec<u8>, _> = trimmed
            .split(',')
            .map(|part| part.trim().parse::<u8>())
            .collect();
        if let Ok(parts) = parts {
            if parts.len() == 3 {
                return Ok(Rgb(parts[0], parts[1], parts[2]));
            }
        }
    }

    Err(format!(
        "Invalid color '{trimmed}'. Use a color name, hex (#00FF00), or RGB (0,255,0)"
    ))
}

fn named_color(name: &str) -> Option<Rgb> {
    Some(match name {
        "black" => Rgb(0, 0, 0),
        "red" => Rgb(255, 0, 0),
        "green" => Rgb(0, 255, 0),
        "yellow" => Rgb(255, 255, 0),
        "blue" => Rgb(0, 0, 255),
        "magenta" => Rgb(255, 0, 255),
        "cyan" => Rgb(0, 255, 255),
        "white" => Rgb(255, 255, 255),
        "gray" | "grey" => Rgb(128, 128, 128),
        "bright_red" => Rgb(255, 64, 64),
        "bright_green" => Rgb(64, 255, 64),
        "bright_yellow" => Rgb(255, 255, 64),
        "bright_blue" => Rgb(64, 64, 255),
        "bright_magenta" => Rgb(255, 64, 255),
        "bright_cyan" => Rgb(64, 255, 255),
        "bright_white" => Rgb(255, 255, 255),
        _ => return None,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_named_hex_and_rgb_colors() {
        assert_eq!(parse_color("BLUE").unwrap(), Rgb(0, 0, 255));
        assert_eq!(parse_color("#00ffcc").unwrap(), Rgb(0, 255, 204));
        assert_eq!(parse_color("128, 64, 192").unwrap(), Rgb(128, 64, 192));
    }

    #[test]
    fn rejects_invalid_colors() {
        assert!(parse_color("#FFFF").is_err());
        assert!(parse_color("256,0,0").is_err());
        assert!(parse_color("not-a-color").is_err());
    }
}
