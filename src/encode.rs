use crate::config::{LCD_HEIGHT, LCD_WIDTH};
use anyhow::{anyhow, Context, Result};
use image::imageops::FilterType;
use image::{DynamicImage, RgbImage};
use std::io::Write;
use std::process::{Command, Stdio};

pub fn encode_h264(image: &RgbImage) -> Result<Vec<u8>> {
    let frame = if image.dimensions() == (LCD_WIDTH, LCD_HEIGHT) {
        image.clone()
    } else {
        DynamicImage::ImageRgb8(image.clone())
            .resize_exact(LCD_WIDTH, LCD_HEIGHT, FilterType::Lanczos3)
            .to_rgb8()
    };

    let mut child = Command::new("ffmpeg")
        .args([
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            "480x480",
            "-i",
            "pipe:0",
            "-frames:v",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-profile:v",
            "baseline",
            "-level",
            "3.0",
            "-crf",
            "25",
            "-x264-params",
            "cabac=0:ref=1:deblock=0:0:0:analyse=0:0:me=dia:subme=0:keyint=24:keyint_min=2:scenecut=0:bframes=0:mbtree=0",
            "-f",
            "h264",
            "pipe:1",
        ])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .context("failed to start ffmpeg; ensure ffmpeg is installed")?;

    child
        .stdin
        .as_mut()
        .context("failed to open ffmpeg stdin")?
        .write_all(frame.as_raw())
        .context("failed to send frame to ffmpeg")?;

    let output = child
        .wait_with_output()
        .context("failed to wait for ffmpeg")?;
    if !output.status.success() {
        return Err(anyhow!(
            "ffmpeg failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    Ok(output.stdout)
}

#[cfg(test)]
mod tests {
    use super::*;
    use image::Rgb;

    #[test]
    fn encodes_h264_if_ffmpeg_is_available() {
        if Command::new("ffmpeg").arg("-version").output().is_err() {
            return;
        }
        let image = RgbImage::from_pixel(480, 480, Rgb([255, 0, 0]));
        let data = encode_h264(&image).unwrap();
        assert!(!data.is_empty());
        assert!(data.windows(4).any(|window| window == [0, 0, 0, 1]));
    }
}
