"""Command-line interface for gaii-control."""

import argparse
from typing import Tuple, Any
from .config import DEFAULT_RGB_COLOR, DEFAULT_FPS, DEFAULT_BG_MODE, DEFAULT_OVERLAY_OPACITY, SCALING_MODES
from .config_loader import load_config, find_config_file


def parse_color(color_str: str) -> Tuple[int, int, int]:
    """Parse color from name, hex (#RRGGBB or RRGGBB), or r,g,b format.
    
    Args:
        color_str: Color string in name, hex, or RGB format
        
    Returns:
        tuple: (R, G, B) values 0-255
        
    Raises:
        argparse.ArgumentTypeError: If color format is invalid
    """
    from .config import COLOR_TEMPLATES
    
    color_str = color_str.strip()
    color_lower = color_str.lower()
    
    # Check for named color first
    if color_lower in COLOR_TEMPLATES:
        return COLOR_TEMPLATES[color_lower]
    
    # Hex format: #RRGGBB or RRGGBB
    hex_str = color_str
    if hex_str.startswith("#"):
        hex_str = hex_str[1:]
    if len(hex_str) == 6:
        try:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return (r, g, b)
        except ValueError:
            pass

    # RGB format: r,g,b
    if "," in color_str:
        try:
            parts = [int(x.strip()) for x in color_str.split(",")]
            if len(parts) == 3 and all(0 <= x <= 255 for x in parts):
                return (parts[0], parts[1], parts[2])
        except ValueError:
            pass

    # Build list of available color names for error message
    available_colors = ", ".join(sorted(COLOR_TEMPLATES.keys()))
    raise argparse.ArgumentTypeError(
        f"Invalid color '{color_str}'. Use a color name ({available_colors}), hex (#00FF00), or RGB (0,255,0)"
    )


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured parser for CLI args
    """
    parser = argparse.ArgumentParser(
        description="Lian Li Galahad II LCD control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Default cyan RGB light
  %(prog)s --rgb blue               # Blue RGB light
  %(prog)s --rgb red                # Red RGB light
  %(prog)s --rgb "#00FF00"          # Green RGB light (hex)
  %(prog)s --rgb "255,0,128"        # Pink RGB light (r,g,b format)
  %(prog)s --rgb bright_yellow --fps 10 # Bright yellow light, 10 FPS
  
Background image examples:
  %(prog)s --bg wallpaper.png                 # With overlay
  %(prog)s --bg photo.jpg --no-overlay        # Image only
  %(prog)s --bg logo.png --bg-mode fit        # Fit with bars
  %(prog)s --bg art.png --overlay-opacity 200 # More opaque overlay

Preset mode examples:
  %(prog)s --preset matrix                    # Matrix falling characters
  %(prog)s --preset matrix --fps 15           # Matrix mode with faster animation
        """,
    )
    parser.add_argument(
        "--rgb",
        "-c",
        type=parse_color,
        default=DEFAULT_RGB_COLOR,
        metavar="COLOR",
        help=f"RGB light color: name, hex (#RRGGBB), or r,g,b (default: {DEFAULT_RGB_COLOR})",
    )
    parser.add_argument(
        "--fps",
        "-f",
        type=float,
        default=DEFAULT_FPS,
        help=f"Display refresh rate in FPS (default: {DEFAULT_FPS})",
    )
    parser.add_argument(
        "--bg",
        "--background",
        type=str,
        default=None,
        metavar="PATH",
        help="Background image file (PNG, JPG, etc.)",
    )
    parser.add_argument(
        "--bg-mode",
        choices=SCALING_MODES,
        default=DEFAULT_BG_MODE,
        help=f"Background scaling mode: {', '.join(SCALING_MODES)} (default: {DEFAULT_BG_MODE})",
    )
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Disable time/date/CPU overlay (show image only)",
    )
    parser.add_argument(
        "--overlay-opacity",
        type=int,
        default=DEFAULT_OVERLAY_OPACITY,
        metavar="0-255",
        help=f"Overlay background opacity (0=transparent, 255=solid) (default: {DEFAULT_OVERLAY_OPACITY})",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        metavar="PRESET",
        choices=["matrix"],
        help="Display preset mode: matrix (falling characters with CPU temp)",
    )
    return parser


def parse_args(argv: list[str] | None = None, load_config_file: bool = True) -> argparse.Namespace:
    """Parse command-line arguments with optional config file support.
    
    Args:
        argv: List of arguments to parse (None uses sys.argv)
        load_config_file: Whether to load config from file (default: True)
        
    Returns:
        argparse.Namespace: Parsed arguments with config values merged
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Validate overlay opacity
    args.overlay_opacity = max(0, min(255, args.overlay_opacity))
    
    # Load and merge config file if available
    if load_config_file:
        config_path = find_config_file()
        if config_path:
            try:
                config_data = load_config(config_path)
                _apply_config_to_args(args, config_data)
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}")
    
    return args


def _apply_config_to_args(args: argparse.Namespace, config: dict[str, Any]) -> None:
    """Apply configuration file values to parsed arguments.
    
    Config file values are used only if CLI args have default values.
    This ensures CLI args always take precedence.
    
    Args:
        args: argparse.Namespace to modify
        config: Configuration dictionary from file
    """
    # Map config keys to argument attributes
    mappings = [
        ("rgb", "rgb", DEFAULT_RGB_COLOR),
        ("fps", "fps", DEFAULT_FPS),
        ("bg", "bg", None),
        ("background", "bg", None),  # Alias
        ("bg_mode", "bg_mode", DEFAULT_BG_MODE),
        ("overlay_opacity", "overlay_opacity", DEFAULT_OVERLAY_OPACITY),
    ]
    
    for config_key, arg_attr, default_value in mappings:
        if config_key in config:
            config_val = config[config_key]
            
            # Special handling for rgb color strings
            if config_key == "rgb" and isinstance(config_val, str):
                try:
                    config_val = parse_color(config_val)
                except argparse.ArgumentTypeError:
                    continue
            
            # Only apply config value if CLI arg has default value
            current_val = getattr(args, arg_attr, None)
            if current_val == default_value or (config_key == "bg" and current_val is None):
                setattr(args, arg_attr, config_val)
    
    # Handle boolean overlay option (inverted)
    if "overlay" in config:
        overlay_enabled = config["overlay"]
        # If config says overlay is False, and CLI didn't explicitly set --no-overlay
        if not overlay_enabled and not args.no_overlay:  # type: ignore
            args.no_overlay = True  # type: ignore
