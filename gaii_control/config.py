"""Configuration constants for gaii-control."""

from typing import Tuple, Dict

# USB Device identifiers
VENDOR_ID: int = 0x0416
PRODUCT_ID: int = 0x7395
INTERFACE_CONTROL: int = 1

# Display specifications
LCD_WIDTH: int = 480
LCD_HEIGHT: int = 480
DISPLAY_SIZE: Tuple[int, int] = (LCD_WIDTH, LCD_HEIGHT)

# Default colors
DEFAULT_RGB_COLOR: Tuple[int, int, int] = (0, 255, 200)  # Cyan
DEFAULT_DARK_BG: Tuple[int, int, int] = (30, 30, 30)
DEFAULT_DARK_RECT: Tuple[int, int, int] = (10, 10, 10)

# Default CLI settings
DEFAULT_FPS: float = 5.0
DEFAULT_BG_MODE: str = "fill"
DEFAULT_OVERLAY_OPACITY: int = 180

# Text rendering positions (x, y) for 480x480 display
TEXT_POSITIONS: Dict[str, Tuple[int, int]] = {
    "cpu_temp": (60, 100),
    "cpu_usage": (420, 100),
    "time": (240, 180),
    "date": (240, 290),
}

# Font sizes for different text elements
FONT_SIZES: Dict[str, int] = {
    "time": 90,
    "cpu": 35,
    "date": 45,
}

# Font color palette
COLOR_CYAN: Tuple[int, int, int] = (0, 200, 255)
COLOR_ORANGE: Tuple[int, int, int] = (255, 160, 0)
COLOR_BRIGHT_CYAN: Tuple[int, int, int] = (0, 255, 200)
COLOR_GRAY: Tuple[int, int, int] = (120, 120, 120)

# Named color templates (16 standard colors)
COLOR_TEMPLATES: Dict[str, Tuple[int, int, int]] = {
    # Basic colors (8)
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "yellow": (255, 255, 0),
    "blue": (0, 0, 255),
    "magenta": (255, 0, 255),
    "cyan": (0, 255, 255),
    "white": (255, 255, 255),
    # Bright colors (8)
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),  # Alias
    "bright_red": (255, 64, 64),
    "bright_green": (64, 255, 64),
    "bright_yellow": (255, 255, 64),
    "bright_blue": (64, 64, 255),
    "bright_magenta": (255, 64, 255),
    "bright_cyan": (64, 255, 255),
    "bright_white": (255, 255, 255),
}

# USB Protocol constants
class USBProtocol:
    """USB packet structure constants for Lian Li Galahad II LCD."""
    HEADER_BYTE_1 = 0x02
    HEADER_BYTE_2 = 0x0D
    CHUNK_SIZE = 1013
    MAX_PACKET_SIZE = 1024
    PACKET_HEADER_SIZE = 11
    TIMEOUT_MS = 2000
    SLEEP_BETWEEN_PACKETS_S = 0.001

# RGB pump color control packet structure
class RGBPacket:
    """RGB pump color control packet format."""
    SIZE = 64
    HEADER_BYTE = 0x01
    COLOR_CMD = 0x83
    COLOR_OFFSET = 5
    PAYLOAD_OFFSET = 6
    PAYLOAD_SIZE = 19

# Video frame packet header structure
class VideoPacket:
    """Video frame packet header byte offsets."""
    HEADER_1 = 0  # 0x02
    HEADER_2 = 1  # 0x0D
    DATA_LEN_B3 = 2  # High byte
    DATA_LEN_B2 = 3
    DATA_LEN_B1 = 4
    DATA_LEN_B0 = 5  # Low byte
    SEQ_B2 = 6  # High byte
    SEQ_B1 = 7
    SEQ_B0 = 8  # Low byte
    CHUNK_LEN_B1 = 9  # High byte
    CHUNK_LEN_B0 = 10  # Low byte
    PAYLOAD = 11

# Temperature sensor names (system-dependent)
TEMP_SENSORS: list[str] = ["coretemp", "k10temp"]

# Image scaling modes
SCALING_MODES: list[str] = ["stretch", "fit", "fill"]
