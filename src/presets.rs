use crate::config::{LCD_HEIGHT, LCD_WIDTH};
use crate::metrics::{cpu_temperature, CpuMeter};
use crate::render::Fonts;
use ab_glyph::PxScale;
use image::{Rgb, RgbImage};
use imageproc::drawing::{draw_filled_rect_mut, draw_text_mut, text_size};
use imageproc::rect::Rect;
use rand::Rng;

pub trait Preset {
    fn render(&mut self, fonts: &Fonts, cpu: &mut CpuMeter) -> RgbImage;
}

struct MatrixColumn {
    y: f32,
    ch: char,
    speed: f32,
    trail_len: usize,
}

pub struct MatrixPreset {
    columns: Vec<MatrixColumn>,
    chars: Vec<char>,
}

impl MatrixPreset {
    pub fn new() -> Self {
        let chars: Vec<char> = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
            .chars()
            .collect();
        let mut rng = rand::thread_rng();
        let columns = (0..(LCD_WIDTH / 10))
            .map(|_| MatrixColumn {
                y: rng.gen_range(-200.0..0.0),
                ch: chars[rng.gen_range(0..chars.len())],
                speed: rng.gen_range(1.5..3.0),
                trail_len: rng.gen_range(5..15),
            })
            .collect();
        Self { columns, chars }
    }
}

impl Default for MatrixPreset {
    fn default() -> Self {
        Self::new()
    }
}

impl Preset for MatrixPreset {
    fn render(&mut self, fonts: &Fonts, _cpu: &mut CpuMeter) -> RgbImage {
        let mut img = RgbImage::from_pixel(LCD_WIDTH, LCD_HEIGHT, Rgb([0, 0, 0]));
        let mut rng = rand::thread_rng();
        if let Some(font) = fonts.regular() {
            for (idx, col) in self.columns.iter_mut().enumerate() {
                col.y += col.speed;
                if col.y > LCD_HEIGHT as f32 + 100.0 {
                    col.y = -200.0;
                    col.ch = self.chars[rng.gen_range(0..self.chars.len())];
                    col.speed = rng.gen_range(1.5..3.0);
                }
                for trail in 0..col.trail_len {
                    let y = col.y - trail as f32 * 15.0;
                    if y > -20.0 && y < LCD_HEIGHT as f32 + 20.0 {
                        let brightness = 1.0 - trail as f32 / col.trail_len as f32;
                        let color = if brightness > 0.75 {
                            Rgb([0, 255, 0])
                        } else if brightness > 0.5 {
                            Rgb([0, 200, 0])
                        } else if brightness > 0.25 {
                            Rgb([0, 100, 0])
                        } else {
                            Rgb([0, 50, 0])
                        };
                        draw_text_mut(
                            &mut img,
                            color,
                            idx as i32 * 10 + 2,
                            y as i32,
                            PxScale::from(12.0),
                            font,
                            &col.ch.to_string(),
                        );
                    }
                }
            }
        }

        let temp = cpu_temperature()
            .map(|t| format!("{t}°C"))
            .unwrap_or_else(|| "N/A".to_string());
        if let Some(font) = fonts.bold() {
            let scale = PxScale::from(60.0);
            let (tw, th) = text_size(scale, font, &temp);
            let x = LCD_WIDTH as i32 / 2 - tw as i32 / 2;
            let y = LCD_HEIGHT as i32 / 2 - th as i32 / 2;
            draw_filled_rect_mut(
                &mut img,
                Rect::at(x - 10, y - 10).of_size(tw + 20, th + 20),
                Rgb([0, 30, 0]),
            );
            draw_text_mut(&mut img, Rgb([0, 255, 0]), x, y, scale, font, &temp);
        }
        img
    }
}

pub struct HeartbeatPreset {
    frame: u64,
    fps: f32,
}

impl HeartbeatPreset {
    pub fn new(fps: f32) -> Self {
        Self { frame: 0, fps }
    }
}

impl Preset for HeartbeatPreset {
    fn render(&mut self, fonts: &Fonts, cpu: &mut CpuMeter) -> RgbImage {
        let mut img = RgbImage::from_pixel(LCD_WIDTH, LCD_HEIGHT, Rgb([0, 0, 0]));
        let load = cpu.usage_percent();
        let color = color_for_load(load);
        let blocks = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];
        let mut bar = String::from("|");
        for i in (0..8).rev() {
            bar.push(blocks[pulse_idx(i, load, self.frame, self.fps)]);
        }
        for i in 0..8 {
            bar.push(blocks[pulse_idx(i, load, self.frame, self.fps)]);
        }
        bar.push('|');

        if let Some(font) = fonts.bold() {
            let cpu_text = format!("{}%", load.round() as u32);
            let cpu_scale = PxScale::from(48.0);
            let (cw, ch) = text_size(cpu_scale, font, &cpu_text);
            let cx = LCD_WIDTH as i32 / 2 - cw as i32 / 2;
            let cy = LCD_HEIGHT as i32 / 2 - ch as i32 / 2 - 80;
            draw_text_mut(
                &mut img,
                dim(color),
                cx + 10,
                cy - 40,
                PxScale::from(20.0),
                font,
                "CPU LOAD",
            );
            draw_filled_rect_mut(
                &mut img,
                Rect::at(cx - 15, cy - 15).of_size(cw + 30, ch + 30),
                Rgb([20, 20, 20]),
            );
            draw_text_mut(&mut img, color, cx, cy, cpu_scale, font, &cpu_text);

            let bar_scale = PxScale::from(80.0);
            let (bw, bh) = text_size(bar_scale, font, &bar);
            draw_text_mut(
                &mut img,
                color,
                LCD_WIDTH as i32 / 2 - bw as i32 / 2,
                LCD_HEIGHT as i32 / 2 - bh as i32 / 2 + 40,
                bar_scale,
                font,
                &bar,
            );
        }

        self.frame += 1;
        img
    }
}

fn pulse_idx(segment: usize, load: f32, frame: u64, fps: f32) -> usize {
    let base = (load / 80.0).min(1.2);
    let pulse_speed = 2.0 + (load / 100.0) * 4.0;
    let phase = (frame as f32 / fps.max(1.0)) * pulse_speed + segment as f32 * 0.4;
    let wave = (phase.sin() + 1.0) / 2.0;
    let boost = 1.0 - (segment as f32 / 8.0) * 0.4;
    ((base * wave * boost).clamp(0.0, 1.0) * 7.0) as usize
}

fn color_for_load(load: f32) -> Rgb<u8> {
    if load < 50.0 {
        Rgb([(load / 50.0 * 100.0) as u8, 255, 0])
    } else if load < 75.0 {
        Rgb([(100.0 + ((load - 50.0) / 25.0) * 155.0) as u8, 255, 0])
    } else {
        Rgb([
            255,
            (255.0 * (1.0 - ((load - 75.0) / 25.0).clamp(0.0, 1.0))) as u8,
            0,
        ])
    }
}

fn dim(color: Rgb<u8>) -> Rgb<u8> {
    Rgb([color[0] / 2, color[1] / 2, color[2] / 2])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn presets_render_display_size() {
        let fonts = Fonts::load();
        let mut cpu = CpuMeter::default();
        assert_eq!(
            MatrixPreset::new().render(&fonts, &mut cpu).dimensions(),
            (480, 480)
        );
        assert_eq!(
            HeartbeatPreset::new(10.0)
                .render(&fonts, &mut cpu)
                .dimensions(),
            (480, 480)
        );
    }
}
