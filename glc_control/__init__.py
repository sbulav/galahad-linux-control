"""GAII Control - Lian Li Galahad II LCD control for Linux."""

from .config import (
    VENDOR_ID,
    PRODUCT_ID,
    INTERFACE_CONTROL,
    LCD_WIDTH,
    LCD_HEIGHT,
    DISPLAY_SIZE,
    DEFAULT_RGB_COLOR,
    DEFAULT_FPS,
    DEFAULT_BG_MODE,
    DEFAULT_OVERLAY_OPACITY,
    SCALING_MODES,
)
from .cli import parse_color, parse_args, create_parser
from .config_loader import load_config, find_config_file, create_config_example
from .image_processor import encode_h264, load_background, create_frame
from .presets import Preset, MatrixPreset
from .usb_device import (
    find_device,
    setup_device,
    get_endpoint,
    send_h264_frame,
    set_rgb_color,
    cleanup_device,
)

__version__ = "1.0.0"
__all__ = [
    # Config
    "VENDOR_ID",
    "PRODUCT_ID",
    "INTERFACE_CONTROL",
    "LCD_WIDTH",
    "LCD_HEIGHT",
    "DISPLAY_SIZE",
    "DEFAULT_RGB_COLOR",
    "DEFAULT_FPS",
    "DEFAULT_BG_MODE",
    "DEFAULT_OVERLAY_OPACITY",
    "SCALING_MODES",
    # CLI
    "parse_color",
    "parse_args",
    "create_parser",
    # Config Loading
    "load_config",
    "find_config_file",
    "create_config_example",
    # Image Processing
    "encode_h264",
    "load_background",
    "create_frame",
    # Presets
    "Preset",
    "MatrixPreset",
    # USB Device
    "find_device",
    "setup_device",
    "get_endpoint",
    "send_h264_frame",
    "set_rgb_color",
    "cleanup_device",
]
