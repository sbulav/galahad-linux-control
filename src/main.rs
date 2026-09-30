use anyhow::{anyhow, Result};
use clap::Parser;
use galahad_linux_control::app::{describe_bg, file_mtime, Display, RELOAD_INTERVAL};
use galahad_linux_control::cli::Args;
use galahad_linux_control::config::{effective_rgb, load_settings_from, resolve_config_path};
use galahad_linux_control::encode::encode_h264;
use galahad_linux_control::metrics::CpuMeter;
use galahad_linux_control::render::Fonts;
use galahad_linux_control::usb::GalahadDevice;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Instant;

/// Exit (non-zero) after this many frames in a row fail to encode or send.
const MAX_CONSECUTIVE_FRAME_ERRORS: u32 = 10;

fn main() -> Result<()> {
    let args = Args::parse();
    let config_path = resolve_config_path(&args);
    let mut config_stamp = config_path.as_deref().and_then(file_mtime);
    let mut display = Display::new(load_settings_from(&args, config_path.as_deref()));

    let running = Arc::new(AtomicBool::new(true));
    let signal_running = Arc::clone(&running);
    ctrlc::set_handler(move || {
        signal_running.store(false, Ordering::SeqCst);
    })?;

    let fonts = Fonts::load();
    let mut cpu = CpuMeter::default();

    if let Some(mode) = display.settings().preset {
        println!("✅ Using preset mode: {mode}");
    }

    let mut device = match GalahadDevice::open() {
        Ok(device) => device,
        Err(err) => {
            eprintln!("❌ {err}");
            return Err(err);
        }
    };

    let settings = display.settings();
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
            describe_bg(settings),
            settings.show_overlay
        );
    }
    if let Some(path) = &config_path {
        println!("👀 watching config {}", path.display());
    }

    device.set_rgb_color(effective_rgb(display.settings()))?;

    let mut last_check = Instant::now();
    let mut consecutive_errors = 0u32;
    while running.load(Ordering::SeqCst) {
        let started = Instant::now();

        if last_check.elapsed() >= RELOAD_INTERVAL {
            last_check = started;
            let stamp = config_path.as_deref().and_then(file_mtime);
            let bg_changed = display.current_bg_identity() != *display.loaded_bg_identity();
            if stamp != config_stamp || bg_changed {
                config_stamp = stamp;
                let reload = display.apply(load_settings_from(&args, config_path.as_deref()));
                if let Some(rgb) = reload.rgb {
                    if let Err(err) = device.set_rgb_color(rgb) {
                        eprintln!("❌ Error: {err}");
                    }
                }
                println!("🔄 config reloaded: {}", reload.summary());
            }
        }

        let frame = display.render(&fonts, &mut cpu);
        match encode_h264(&frame).and_then(|data| device.send_h264_frame(&data)) {
            Ok(()) => consecutive_errors = 0,
            Err(err) => {
                eprintln!("❌ Error: {err}");
                consecutive_errors += 1;
                if consecutive_errors >= MAX_CONSECUTIVE_FRAME_ERRORS {
                    drop(device);
                    return Err(anyhow!(
                        "giving up after {consecutive_errors} consecutive frame errors"
                    ));
                }
            }
        }

        if let Some(remaining) = display.frame_delay().checked_sub(started.elapsed()) {
            std::thread::sleep(remaining);
        }
    }

    println!("\n⏹️  Stopping by user...");
    println!("Cleaning up resources...");
    drop(device);
    println!("✅ Cleanup complete");
    Ok(())
}
