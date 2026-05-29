use anyhow::Result;
use clap::Parser;
use galahad_linux_control::cli::{Args, PresetMode};
use galahad_linux_control::config::{load_settings, Rgb};
use galahad_linux_control::encode::encode_h264;
use galahad_linux_control::metrics::CpuMeter;
use galahad_linux_control::presets::{HeartbeatPreset, MatrixPreset, Preset};
use galahad_linux_control::render::{create_frame, load_background, Fonts};
use galahad_linux_control::usb::GalahadDevice;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

fn main() -> Result<()> {
    let args = Args::parse();
    let settings = load_settings(args)?;
    let frame_delay = Duration::from_secs_f32(1.0 / settings.fps.max(0.1));

    let running = Arc::new(AtomicBool::new(true));
    let signal_running = Arc::clone(&running);
    ctrlc::set_handler(move || {
        signal_running.store(false, Ordering::SeqCst);
    })?;

    let fonts = Fonts::load();
    let mut cpu = CpuMeter::default();
    let bg = if let (Some(path), None) = (&settings.bg, settings.preset) {
        match load_background(path, settings.bg_mode) {
            Ok(image) => Some(image),
            Err(err) => {
                eprintln!("❌ {err}; falling back to solid colors");
                None
            }
        }
    } else {
        None
    };

    let mut preset: Option<Box<dyn Preset>> = match settings.preset {
        Some(PresetMode::Matrix) => {
            println!("✅ Using preset mode: matrix");
            Some(Box::new(MatrixPreset::new()))
        }
        Some(PresetMode::Heartbeat) => {
            println!("✅ Using preset mode: heartbeat");
            Some(Box::new(HeartbeatPreset::new(settings.fps)))
        }
        None => None,
    };

    let mut device = match GalahadDevice::open() {
        Ok(device) => device,
        Err(err) => {
            eprintln!("❌ {err}");
            return Ok(());
        }
    };

    if let Some(mode) = settings.preset {
        println!(
            "✅ device connected (Preset: {mode}, FPS: {})",
            settings.fps
        );
    } else {
        println!(
            "✅ device connected (RGB: {}, FPS: {}, BG: {}, Overlay: {})",
            settings.rgb,
            settings.fps,
            settings
                .bg
                .as_ref()
                .map(|p| p.display().to_string())
                .unwrap_or_else(|| "solid".into()),
            settings.show_overlay
        );
    }

    let rgb = match settings.preset {
        Some(PresetMode::Matrix) => Rgb(0, 255, 0),
        Some(PresetMode::Heartbeat) => Rgb(255, 0, 0),
        None => settings.rgb,
    };
    device.set_rgb_color(rgb)?;

    while running.load(Ordering::SeqCst) {
        let started = Instant::now();
        let frame = match preset.as_mut() {
            Some(preset) => preset.render(&fonts, &mut cpu),
            None => create_frame(
                bg.as_ref(),
                settings.show_overlay,
                settings.overlay_opacity,
                &fonts,
                &mut cpu,
            ),
        };

        match encode_h264(&frame).and_then(|data| device.send_h264_frame(&data)) {
            Ok(()) => {}
            Err(err) => eprintln!("❌ Error: {err}"),
        }

        if let Some(remaining) = frame_delay.checked_sub(started.elapsed()) {
            std::thread::sleep(remaining);
        }
    }

    println!("\n⏹️  Stopping by user...");
    println!("Cleaning up resources...");
    drop(device);
    println!("✅ Cleanup complete");
    Ok(())
}
