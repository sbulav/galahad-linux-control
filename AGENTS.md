# Agent Guidelines for galahad-linux-control

Rust CLI (`glc`, crate `galahad_linux_control`) that drives the Lian Li Galahad II LCD pump:
renders 480×480 frames, encodes them to H.264 with an external `ffmpeg`, writes them over libusb.

## Dev shell and checks

- `nix develop` — `cargo`, `rustc`, `clippy`, `rustfmt`, `ffmpeg`, libusb and Noto fonts are only
  available inside it. If a host `LD_LIBRARY_PATH` breaks ffmpeg, use `env -u LD_LIBRARY_PATH nix develop`.
- Run all of these before calling a change done:
  - `cargo fmt -- --check`
  - `cargo clippy --all-targets -- -D warnings`
  - `cargo test`
  - `nix build .` (also runs `cargo test`; new files must be `git add`ed or the flake cannot see them)
- `nix run . -- [OPTIONS]` runs against the real pump.

## Module map

- `src/main.rs` — entry point: open device, main render loop, hot-reload polling, error budget.
- `src/app.rs` — `Display` state (settings, background, preset) and `apply` for reload diffs.
- `src/cli.rs` — clap `Args`, `PresetMode`, `ScalingMode`, `parse_color`.
- `src/config.rs` — constants, TOML config file loading, CLI/file merge, `Colors`, `effective_rgb`.
- `src/render.rs` — fonts, background scaling, `create_frame` overlay drawing.
- `src/presets.rs` — `matrix` and `heartbeat` animations (`Preset` trait).
- `src/metrics.rs` — CPU usage (`/proc/stat`) and temperature (hwmon `coretemp`/`k10temp`).
- `src/encode.rs` — `ffmpeg` subprocess wrapper producing baseline H.264.
- `src/protocol.rs` — RGB and H.264 packet construction.
- `src/usb.rs` — `GalahadDevice`: libusb open/claim, bulk writes, cleanup on drop.
- `src/lib.rs` — module declarations and re-exports.

## USB protocol

- Device `0416:7395` (Winbond, `LianLi-GA_II-LCD_v1.4`), control interface `1`, first OUT endpoint.
- Display 480×480. H.264 frames are split into 1024-byte packets (11-byte header + up to
  1013 bytes payload); RGB is a separate 64-byte packet. Both are built in `protocol.rs`.

## Conventions

- rustfmt defaults; clippy clean with `-D warnings`.
- Errors via `anyhow` (`Context` for messages); no new dependencies without a reason.
- Unit tests are hardware-free: they must never open the USB device or require the pump.
  The ffmpeg test skips itself when `ffmpeg` is not on `PATH`.
- Keep USB access in `usb.rs` and out of logic you want to test (`app.rs` returns what to send).

## Hot-reload contract

- About once per second `main` re-stats the config file (mtime) and the background
  (`canonicalize` target + that target's mtime), so re-pointing a `bg` symlink is detected.
- On change, settings are reloaded and only the difference is applied: pump RGB re-sent,
  background reloaded, preset rebuilt, frame delay recomputed; colours/overlay apply next frame.
- A missing `--config` file or a bad value is non-fatal: one warning, then defaults.
- Fatal (non-zero exit, for `Restart=on-failure`): device cannot be opened, or
  10 consecutive frame encode/send failures.
