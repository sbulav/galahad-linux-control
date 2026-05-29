# Galahad Linux Control

Control the LCD screen and RGB lighting on the **Lian Li Galahad II LCD** pump from Linux.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Language: Rust](https://img.shields.io/badge/language-Rust-orange.svg)](https://www.rust-lang.org/)
[![Nix](https://img.shields.io/badge/Nix-supported-5277C3.svg)](https://nixos.org/)

![Matrix preset running on the pump LCD](./assets/matrix-preset.jpg)

`glc` is a small Rust CLI for sending H.264 frames and RGB commands directly to the pump over USB.
It is useful if you want the Galahad II LCD to show Linux system information, a custom image, or one of the built-in animations without running Windows software.

> Supported device: `0416:7395` Winbond Electronics Corp. `LianLi-GA_II-LCD_v1.4`

This project is based on the USB protocol work from [`gaii-control`](https://github.com/bn45hkurr0y4/gaii-control).

## Features

- Show time, date, CPU temperature, and CPU usage on the 480×480 LCD.
- Use a custom background image with `stretch`, `fit`, or `fill` scaling.
- Run animated presets:
  - `matrix`: falling green characters with CPU temperature.
  - `heartbeat`: pulsing CPU load visualization.
- Set pump RGB color by name, hex value, or `r,g,b` triplet.
- Read defaults from a TOML config file.
- Run as a foreground CLI process with clean Ctrl-C shutdown.
- Build and run with Nix or Cargo.

## Quick start

```bash
# Clone the repository
git clone https://github.com/sbulav/galahad-linux-control.git
cd galahad-linux-control

# Run with Nix
nix run . -- --preset matrix
```

If you see a USB permission error, install the udev rule and reconnect the device:

```bash
sudo cp utils/99-lian-li-galahad.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Installation

### Nix / NixOS

Run without installing:

```bash
nix run . -- [OPTIONS]
```

Enter a development shell:

```bash
nix develop
cargo run -- [OPTIONS]
```

On NixOS, add the USB rule to `configuration.nix` so you can run `glc` without root:

```nix
services.udev.extraRules = ''
  SUBSYSTEM=="usb", ATTR{idVendor}=="0416", ATTR{idProduct}=="7395", MODE="0666", GROUP="users"
'';
```

Then rebuild and reconnect the pump USB device.

### Other Linux distributions

Install the system dependencies first. On Debian or Ubuntu:

```bash
sudo apt install libusb-1.0-0-dev pkg-config ffmpeg fonts-noto-core
```

Build from source:

```bash
git clone https://github.com/sbulav/galahad-linux-control.git
cd galahad-linux-control
cargo build --release
```

Install the udev rule:

```bash
sudo cp utils/99-lian-li-galahad.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Reconnect the USB device, then run:

```bash
./target/release/glc [OPTIONS]
```

## Usage

```text
Usage: glc [OPTIONS]

Options:
  -c, --rgb <COLOR>              RGB light color: name, hex (#RRGGBB), or r,g,b
  -f, --fps <FPS>                Display refresh rate in FPS
      --bg <PATH>                Background image file (PNG, JPG, etc.)
      --bg-mode <BG_MODE>        Background scaling mode [possible values: stretch, fit, fill]
      --no-overlay               Disable time/date/CPU overlay
      --overlay-opacity <0-255>  Overlay background opacity (0=transparent, 255=solid)
  -p, --preset <PRESET>          Display preset mode: matrix or heartbeat [possible values: matrix, heartbeat]
  -h, --help                     Print help
```

### Common examples

Set only the pump RGB color and show the default LCD overlay:

```bash
glc --rgb blue
```

Use a custom RGB value:

```bash
glc --rgb "#00FF00"
glc --rgb "255,0,0"
```

Show a background image with the default overlay:

```bash
glc --bg ~/Pictures/wallpaper.png
```

Show an image without text:

```bash
glc --bg ~/Pictures/logo.png --no-overlay
```

Fit a non-square image with black bars:

```bash
glc --bg ~/Pictures/photo.jpg --bg-mode fit
```

Run the matrix preset:

```bash
glc --preset matrix --fps 15
```

Run the heartbeat preset:

```bash
glc --preset heartbeat --fps 20
```

> Presets set the pump RGB automatically: `matrix` uses green, and `heartbeat` uses red.

## Configuration file

`glc` looks for the first existing config file in this order:

1. `~/.config/gaii-control/config.toml`
2. `~/gaii-control.toml`
3. `./gaii-control.toml`

CLI options override config file values.

Example:

```toml
[gaii-control]
rgb = "#00FFC8"
fps = 5.0
bg = "~/Pictures/wallpaper.png"
bg_mode = "fill"
overlay = true
overlay_opacity = 180
```

Supported keys:

| Key | Type | Description |
| --- | --- | --- |
| `rgb` | string | Color name, `#RRGGBB`, `RRGGBB`, or `r,g,b`. |
| `fps` | number | Display refresh rate. |
| `bg` | string | Background image path. |
| `background` | string | Alias for `bg`. |
| `bg_mode` | string | `stretch`, `fit`, or `fill`. |
| `overlay` | boolean | Show or hide the time/date/CPU overlay. |
| `overlay_opacity` | integer | Overlay opacity from `0` to `255`. |

## Colors

You can pass colors in three formats:

```bash
glc --rgb cyan        # named color
glc --rgb "#00FFC8"  # hex
glc --rgb "0,255,0"  # RGB triplet
```

Named colors are case-insensitive.

| Basic colors | Bright colors |
| --- | --- |
| `black` | `gray`, `grey` |
| `red` | `bright_red` |
| `green` | `bright_green` |
| `yellow` | `bright_yellow` |
| `blue` | `bright_blue` |
| `magenta` | `bright_magenta` |
| `cyan` | `bright_cyan` |
| `white` | `bright_white` |

## Background scaling

| Mode | Behavior | Best for |
| --- | --- | --- |
| `stretch` | Resizes to exactly 480×480. May distort the image. | Abstract images or already-square art. |
| `fit` | Preserves aspect ratio and adds black bars if needed. | Photos and logos that must not be cropped. |
| `fill` | Preserves aspect ratio and crops edges to fill the screen. | Wallpapers and full-screen backgrounds. |

## How it works

`glc` talks to the pump through libusb. It renders each frame as a 480×480 RGB image, encodes it to H.264 with `ffmpeg`, splits it into 1024-byte USB packets, and writes those packets to the device endpoint.

The RGB command uses a separate 64-byte USB packet. Packet construction is implemented in Rust and covered by hardware-free tests.

## Development

Use the Nix development shell:

```bash
nix develop
```

Run checks:

```bash
cargo fmt -- --check
cargo clippy -- -D warnings
cargo test
nix build .
```

The automated tests do not require the pump. They cover color parsing, config merging, packet construction, rendering size checks, preset rendering, and H.264 encoding when `ffmpeg` is available.

Real-device validation is still manual:

- USB device discovery and interface claiming.
- RGB color changes.
- LCD playback.
- Long-running FPS stability.

## Troubleshooting

### `device not found`

Check that the pump USB device is visible:

```bash
lsusb | grep -i '0416:7395\|lianli\|winbond'
```

If it is not listed, reconnect the internal USB cable or check the motherboard header.

### `failed to claim USB interface`

Your user probably cannot access the device. Install the udev rule, reload rules, and reconnect the device:

```bash
sudo cp utils/99-lian-li-galahad.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

You can also test with `sudo`, but the udev rule is better for regular use.

### Text is missing or looks wrong

Install Noto fonts and fontconfig. On Debian or Ubuntu:

```bash
sudo apt install fonts-noto-core fontconfig
```

### H.264 encoding fails

Install `ffmpeg` and make sure it is in `PATH`:

```bash
ffmpeg -version
```

### CPU temperature shows `N/A`

Temperature detection is best effort. `glc` currently checks Linux hardware monitor sensors named `coretemp` and `k10temp`. If those sensors are unavailable, the display keeps running and shows `N/A`.

## Project status

The Rust version targets feature parity with the previous Python implementation. It keeps the same CLI, config paths, USB access model, and display behavior where practical.

Known trade-off: H.264 encoding uses an external `ffmpeg` process. This keeps packaging simple, but it may be slower than an in-process encoder.

## Contributing

Issues and pull requests are welcome. Useful contributions include:

- Testing on real Galahad II LCD hardware.
- Improving Linux sensor detection.
- Improving render performance.
- Adding new presets without breaking existing CLI behavior.
- Improving packaging for non-Nix distributions.

Before opening a pull request, run:

```bash
cargo fmt -- --check
cargo clippy -- -D warnings
cargo test
```

## License

This project is licensed under the [MIT License](LICENSE).
