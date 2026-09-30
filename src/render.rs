use crate::cli::ScalingMode;
use crate::config::{Colors, LCD_HEIGHT, LCD_WIDTH};
use crate::metrics::{cpu_temperature, CpuMeter};
use ab_glyph::{FontArc, PxScale};
use anyhow::{Context, Result};
use chrono::Local;
use image::imageops::FilterType;
use image::{DynamicImage, Rgb, RgbImage};
use imageproc::drawing::{draw_filled_rect_mut, draw_text_mut, text_size};
use imageproc::rect::Rect;
use std::path::Path;

pub struct Fonts {
    regular: Option<FontArc>,
    bold: Option<FontArc>,
}

impl Fonts {
    pub fn load() -> Self {
        let mut db = fontdb::Database::new();
        db.load_system_fonts();
        let regular = load_font(&db, "Noto Sans Mono", fontdb::Weight::NORMAL)
            .or_else(|| load_font(&db, "Noto Sans", fontdb::Weight::NORMAL));
        let bold = load_font(&db, "Noto Sans Mono", fontdb::Weight::BOLD)
            .or_else(|| load_font(&db, "Noto Sans", fontdb::Weight::BOLD))
            .or_else(|| regular.clone());
        Self { regular, bold }
    }

    pub fn regular(&self) -> Option<&FontArc> {
        self.regular.as_ref()
    }

    pub fn bold(&self) -> Option<&FontArc> {
        self.bold.as_ref().or(self.regular.as_ref())
    }
}

fn load_font(db: &fontdb::Database, family: &str, weight: fontdb::Weight) -> Option<FontArc> {
    let query = fontdb::Query {
        families: &[fontdb::Family::Name(family)],
        weight,
        ..fontdb::Query::default()
    };
    let id = db.query(&query)?;
    let face = db.face(id)?;
    match &face.source {
        fontdb::Source::File(path) => std::fs::read(path)
            .ok()
            .and_then(|bytes| FontArc::try_from_vec(bytes).ok()),
        fontdb::Source::Binary(data) => FontArc::try_from_vec(data.as_ref().as_ref().to_vec()).ok(),
        _ => None,
    }
}

pub fn load_background(path: impl AsRef<Path>, mode: ScalingMode) -> Result<RgbImage> {
    let img = image::open(path.as_ref())
        .with_context(|| format!("failed to load background '{}'", path.as_ref().display()))?;
    Ok(resize_background(img, mode))
}

pub fn resize_background(img: DynamicImage, mode: ScalingMode) -> RgbImage {
    let img = img.to_rgb8();
    match mode {
        ScalingMode::Stretch => DynamicImage::ImageRgb8(img)
            .resize_exact(LCD_WIDTH, LCD_HEIGHT, FilterType::Lanczos3)
            .to_rgb8(),
        ScalingMode::Fit => {
            let resized = DynamicImage::ImageRgb8(img)
                .resize(LCD_WIDTH, LCD_HEIGHT, FilterType::Lanczos3)
                .to_rgb8();
            let mut canvas = RgbImage::from_pixel(LCD_WIDTH, LCD_HEIGHT, Rgb([0, 0, 0]));
            let x = (LCD_WIDTH - resized.width()) / 2;
            let y = (LCD_HEIGHT - resized.height()) / 2;
            image::imageops::overlay(&mut canvas, &resized, x.into(), y.into());
            canvas
        }
        ScalingMode::Fill => {
            let (w, h) = img.dimensions();
            let scale = (LCD_WIDTH as f32 / w as f32).max(LCD_HEIGHT as f32 / h as f32);
            let new_w = (w as f32 * scale).ceil() as u32;
            let new_h = (h as f32 * scale).ceil() as u32;
            let resized = DynamicImage::ImageRgb8(img)
                .resize_exact(new_w, new_h, FilterType::Lanczos3)
                .to_rgb8();
            let x = (new_w - LCD_WIDTH) / 2;
            let y = (new_h - LCD_HEIGHT) / 2;
            image::imageops::crop_imm(&resized, x, y, LCD_WIDTH, LCD_HEIGHT).to_image()
        }
    }
}

pub fn create_frame(
    bg: Option<&RgbImage>,
    show_overlay: bool,
    overlay_opacity: u8,
    colors: &Colors,
    fonts: &Fonts,
    cpu: &mut CpuMeter,
) -> RgbImage {
    let mut img = match bg {
        Some(bg) => bg.clone(),
        None => {
            let mut img = RgbImage::from_pixel(LCD_WIDTH, LCD_HEIGHT, colors.background.into());
            draw_filled_rect_mut(
                &mut img,
                Rect::at(40, 40).of_size(400, 400),
                colors.panel.into(),
            );
            img
        }
    };

    if !show_overlay {
        return img;
    }

    if bg.is_some() && overlay_opacity > 0 {
        blend_rect(
            &mut img,
            Rect::at(40, 75).of_size(400, 285),
            colors.overlay.into(),
            overlay_opacity,
        );
    }

    let cpu_temp = cpu_temperature()
        .map(|t| format!("{t}°C"))
        .unwrap_or_else(|| "N/A".to_string());
    let cpu_usage = format!("{}%", cpu.usage_percent().round() as u32);
    let now = Local::now();
    let time = now.format("%H:%M:%S").to_string();
    let date = now.format("%d.%m.%Y").to_string();

    if let Some(font) = fonts.bold() {
        draw_text_mut(
            &mut img,
            colors.cpu_temp.into(),
            60,
            100,
            PxScale::from(35.0),
            font,
            &cpu_temp,
        );

        let (tw, _) = text_size(PxScale::from(35.0), font, &cpu_usage);
        draw_text_mut(
            &mut img,
            colors.cpu_usage.into(),
            420 - tw as i32,
            100,
            PxScale::from(35.0),
            font,
            &cpu_usage,
        );

        let (tw, _) = text_size(PxScale::from(90.0), font, &time);
        draw_text_mut(
            &mut img,
            colors.time.into(),
            240 - tw as i32 / 2,
            180,
            PxScale::from(90.0),
            font,
            &time,
        );

        let (tw, _) = text_size(PxScale::from(45.0), font, &date);
        draw_text_mut(
            &mut img,
            colors.date.into(),
            240 - tw as i32 / 2,
            290,
            PxScale::from(45.0),
            font,
            &date,
        );
    }

    img
}

fn blend_rect(img: &mut RgbImage, rect: Rect, color: Rgb<u8>, alpha: u8) {
    let alpha = alpha as f32 / 255.0;
    // Rect::right()/bottom() are inclusive; derive exclusive bounds from the size.
    let clamp = |value: i64, max: u32| value.clamp(0, max as i64) as u32;
    let left = clamp(rect.left() as i64, img.width());
    let top = clamp(rect.top() as i64, img.height());
    let right = clamp(rect.left() as i64 + rect.width() as i64, img.width());
    let bottom = clamp(rect.top() as i64 + rect.height() as i64, img.height());
    for y in top..bottom {
        for x in left..right {
            let p = img.get_pixel_mut(x, y);
            for (channel, color_value) in color.0.iter().enumerate() {
                p.0[channel] =
                    (p.0[channel] as f32 * (1.0 - alpha) + *color_value as f32 * alpha) as u8;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_background_modes_return_display_size() {
        let img = DynamicImage::ImageRgb8(RgbImage::from_pixel(1000, 100, Rgb([255, 0, 0])));
        for mode in [ScalingMode::Stretch, ScalingMode::Fit, ScalingMode::Fill] {
            let resized = resize_background(img.clone(), mode);
            assert_eq!(resized.dimensions(), (480, 480));
        }
    }

    #[test]
    fn fit_mode_letterboxes() {
        let img = DynamicImage::ImageRgb8(RgbImage::from_pixel(1000, 100, Rgb([255, 0, 0])));
        let resized = resize_background(img, ScalingMode::Fit);
        assert_eq!(resized.get_pixel(0, 0), &Rgb([0, 0, 0]));
    }

    #[test]
    fn create_frame_returns_display_size() {
        let fonts = Fonts::load();
        let mut cpu = CpuMeter::default();
        let frame = create_frame(None, true, 180, &Colors::default(), &fonts, &mut cpu);
        assert_eq!(frame.dimensions(), (480, 480));
    }

    #[test]
    fn create_frame_uses_configured_colors() {
        let fonts = Fonts::load();
        let mut cpu = CpuMeter::default();
        let colors = Colors {
            background: crate::config::Rgb(1, 2, 3),
            panel: crate::config::Rgb(4, 5, 6),
            ..Colors::default()
        };
        let frame = create_frame(None, false, 180, &colors, &fonts, &mut cpu);
        assert_eq!(frame.get_pixel(0, 0), &Rgb([1, 2, 3]));
        assert_eq!(frame.get_pixel(240, 50), &Rgb([4, 5, 6]));
    }

    #[test]
    fn blend_rect_covers_last_column_and_row() {
        let mut img = RgbImage::from_pixel(480, 480, Rgb([255, 255, 255]));
        blend_rect(
            &mut img,
            Rect::at(40, 75).of_size(400, 285),
            Rgb([0, 0, 0]),
            255,
        );
        assert_eq!(img.get_pixel(40, 75), &Rgb([0, 0, 0]));
        assert_eq!(img.get_pixel(439, 359), &Rgb([0, 0, 0]));
        assert_eq!(img.get_pixel(440, 359), &Rgb([255, 255, 255]));
        assert_eq!(img.get_pixel(439, 360), &Rgb([255, 255, 255]));
        assert_eq!(img.get_pixel(39, 74), &Rgb([255, 255, 255]));
    }

    #[test]
    fn blend_rect_clamps_to_image() {
        let mut img = RgbImage::from_pixel(10, 10, Rgb([255, 255, 255]));
        blend_rect(
            &mut img,
            Rect::at(-5, 5).of_size(100, 100),
            Rgb([0, 0, 0]),
            255,
        );
        assert_eq!(img.get_pixel(0, 9), &Rgb([0, 0, 0]));
        assert_eq!(img.get_pixel(9, 4), &Rgb([255, 255, 255]));
    }
}
