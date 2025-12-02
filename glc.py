#!/usr/bin/env python3
"""
Lian Li Galahad II LCD Control for Linux

This is the main entry point. The core functionality has been modularized
into the gaii_control package for better maintainability and testability.
"""

import time
from gaii_control import (
    parse_args,
    find_device,
    setup_device,
    get_endpoint,
    set_rgb_color,
    send_h264_frame,
    load_background,
    create_frame,
    encode_h264,
    cleanup_device,
    MatrixPreset,
)


def main() -> None:
    args = parse_args()

    rgb_color = args.rgb
    frame_delay = 1.0 / args.fps
    show_overlay = not args.no_overlay
    overlay_opacity = args.overlay_opacity
    preset_mode = args.preset

    # Initialize preset if specified
    preset = None
    if preset_mode:
        if preset_mode == "matrix":
            preset = MatrixPreset(fps=args.fps)
            print(f"✅ Using preset mode: {preset_mode}")
        else:
            print(f"❌ Unknown preset mode: {preset_mode}")
            return

    # Load background if provided (not used in preset mode)
    bg_image = None
    if args.bg and not preset_mode:
        bg_image = load_background(args.bg, args.bg_mode)
        if bg_image is None:
            print("❌ Failed to load background, falling back to solid colors")
            bg_image = None

    device = find_device()
    if device is None:
        print("❌ device not found!")
        return

    setup_device(device)

    endpoint = get_endpoint(device)

    if preset_mode:
        print(
            f"✅ device connected (Preset: {preset_mode}, FPS: {args.fps})"
        )
    else:
        print(
            f"✅ device connected (RGB: {rgb_color}, FPS: {args.fps}, BG: {args.bg or 'solid'}, Overlay: {show_overlay})"
        )

    # Set RGB color (green for matrix preset)
    if preset_mode == "matrix":
        # Force green theme for matrix
        set_rgb_color(endpoint, (0, 255, 0))
    else:
        set_rgb_color(endpoint, rgb_color)

    try:
        while True:
            if preset:
                # Use preset rendering
                img = preset.render()
            else:
                # Use standard frame rendering
                img = create_frame(bg_image, show_overlay, overlay_opacity)
            
            h264_data = encode_h264(img)

            if h264_data:
                send_h264_frame(endpoint, h264_data)

            time.sleep(frame_delay)

    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping by user...")
        print("Cleaning up resources...")
        cleanup_device(device)
        print("✅ Cleanup complete")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Cleaning up resources...")
        cleanup_device(device)
        print("✅ Cleanup complete")

    finally:
        # Catch-all: ensure cleanup happens for any exit path
        # (SystemExit, other signals, etc)
        try:
            cleanup_device(device)
        except:
            pass


if __name__ == "__main__":
    main()
