"""Configuration file loader for gaii-control.

Supports loading settings from ~/.config/gaii-control/config.toml
CLI arguments override configuration file values.
"""

from typing import Any, Dict, Tuple
import os
import sys

# Try to import tomllib (Python 3.11+) or tomli (fallback)
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


DEFAULT_CONFIG_PATHS: list[str] = [
    os.path.expanduser("~/.config/gaii-control/config.toml"),
    os.path.expanduser("~/gaii-control.toml"),
    "./gaii-control.toml",
]


def find_config_file() -> str | None:
    """Find the first existing config file from default locations.
    
    Returns:
        Path to config file if found, None otherwise
    """
    for path in DEFAULT_CONFIG_PATHS:
        if os.path.exists(path):
            return path
    return None


def load_config(config_path: str | None = None) -> Dict[str, Any]:
    """Load configuration from a TOML file.
    
    Args:
        config_path: Path to config file. If None, searches default locations.
        
    Returns:
        Dictionary with configuration values, or empty dict if not found.
        
    Raises:
        RuntimeError: If TOML support is not available
    """
    if tomllib is None:
        raise RuntimeError(
            "TOML support not available. Install 'tomli' package for Python < 3.11"
        )
    
    # Find config file if path not specified
    if config_path is None:
        config_path = find_config_file()
        if config_path is None:
            return {}
    
    # Load config file
    try:
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)
        
        # Extract gaii-control section if present
        if "gaii-control" in config_data:
            return config_data["gaii-control"]
        return config_data
    
    except FileNotFoundError:
        print(f"Warning: Config file not found: {config_path}", file=sys.stderr)
        return {}
    
    except Exception as e:
        print(f"Warning: Failed to load config file: {e}", file=sys.stderr)
        return {}


def merge_config_with_args(
    config: Dict[str, Any], cli_args: Any
) -> Dict[str, Any]:
    """Merge configuration file values with CLI arguments.
    
    CLI arguments take precedence over config file values.
    
    Args:
        config: Configuration from file
        cli_args: argparse.Namespace from CLI parsing
        
    Returns:
        Merged configuration dictionary
    """
    merged: Dict[str, Any] = {**config}
    
    # Map config file keys to CLI argument names
    key_mapping = {
        "rgb": "rgb",
        "fps": "fps",
        "bg": "bg",
        "background": "bg",  # Alias support
        "bg_mode": "bg_mode",
        "overlay": "no_overlay",  # Note: inverted
        "overlay_opacity": "overlay_opacity",
    }
    
    # Override with CLI values if they were explicitly provided
    for config_key, arg_key in key_mapping.items():
        if hasattr(cli_args, arg_key):
            arg_value = getattr(cli_args, arg_key)
            
            # Special handling for 'overlay' (inverted logic)
            if config_key == "overlay":
                # If user specified --no-overlay on CLI, don't override with config
                if cli_args.no_overlay is not True:  # type: ignore
                    merged["overlay"] = config.get("overlay", True)
            else:
                # Don't override if CLI arg is at its default value
                # This is a heuristic; a better approach would track explicitly
                # provided args, but this is a good compromise
                if arg_value is not None:
                    merged[arg_key] = arg_value
    
    return merged


def create_config_example(output_path: str) -> None:
    """Create an example configuration file.
    
    Args:
        output_path: Where to write the example config file
    """
    example_config = """# Lian Li Galahad II LCD Control Configuration
# Place this file at ~/.config/gaii-control/config.toml

[gaii-control]

# RGB pump color (hex #RRGGBB or r,g,b format)
rgb = "#00FFC8"  # Cyan (default)

# Display refresh rate in FPS
fps = 5.0

# Background image path (optional)
# bg = "/path/to/image.png"

# Background scaling mode: "stretch", "fit", or "fill"
bg_mode = "fill"

# Show time/date/CPU overlay
overlay = true

# Overlay background opacity (0=transparent, 255=solid)
overlay_opacity = 180

# Examples:
# rgb = "#FF0000"        # Red
# rgb = "0,255,0"        # Green
# rgb = "0, 0, 255"      # Blue
# bg = "~/Pictures/wallpaper.png"
# bg_mode = "fit"
# overlay = false
"""
    
    try:
        # Create directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write example config
        with open(output_path, "w") as f:
            f.write(example_config)
        
        print(f"✅ Created example config at: {output_path}")
    except Exception as e:
        print(f"❌ Failed to create config file: {e}", file=sys.stderr)
