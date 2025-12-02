# Agent Guidelines for galahad-linux-control

## Build & Run

- **Dev shell**: `nix develop` (provides Python 3.13, pyusb, pillow, psutil, libusb1, ffmpeg, noto-fonts)
- **Run directly**: `nix run .`
- **Run script**: `python glc.py [OPTIONS]`
- **No tests exist** - this is a single-file Python CLI tool

## Code Style (Python)

- **Formatting**: PEP 8 with 4-space indentation
- **Imports**: Standard library first, then third-party (usb, PIL, psutil)
- **Types**: No type hints currently used; add them when modifying functions
- **Naming**: snake_case for functions/variables, UPPER_CASE for constants (VENDOR_ID, PRODUCT_ID)
- **Error handling**: Broad `except:` clauses are acceptable for hardware/temporary failures; avoid in general code
- **Documentation**: Docstrings for public functions (e.g., `load_background()`, `parse_color()`)
- **Line length**: ~100 characters (no hard limit enforced)

## Repository Structure

- **glc.py**: Single 414-line script handling USB device control, frame rendering, H.264 encoding
- **flake.nix**: NixOS development environment + package definition
- **99-lian-li-galahad.rules**: udev rules for non-root USB access
- **readme.md**: User documentation

## Key Functions

- `create_frame()`: Renders clock/CPU/date overlay on background image
- `encode_h264()`: Wraps ffmpeg to convert PNG → H.264 for LCD display
- `send_h264_frame()`: Chunks and sends H.264 data to USB device
- `load_background()`: Handles image resizing with stretch/fit/fill modes
- `parse_color()`: CLI color argument parser (#RRGGBB or r,g,b)

## Notes

- Device: Lian Li Galahad II LCD (Winbond 0416:7395)
- Display: 480×480 pixels
- No automatic formatting tool configured; maintain consistency with existing code
