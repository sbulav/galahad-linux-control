"""Image processing and frame rendering for gaii-control."""

from typing import Any, Dict, Tuple
import subprocess
import tempfile
import os
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import psutil

from .config import (
    DISPLAY_SIZE,
    DEFAULT_DARK_BG,
    DEFAULT_DARK_RECT,
    TEXT_POSITIONS,
    FONT_SIZES,
    COLOR_CYAN,
    COLOR_ORANGE,
    COLOR_BRIGHT_CYAN,
    COLOR_GRAY,
    TEMP_SENSORS,
    SCALING_MODES,
)


def encode_h264(image: Image.Image) -> bytes:
    """Encode PIL Image to H.264 format using ffmpeg.
    
    Args:
        image: PIL Image object to encode
        
    Returns:
        bytes: H.264 encoded video data
    """
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_in:
        image.save(tmp_in.name)
        input_file = tmp_in.name

    with tempfile.NamedTemporaryFile(suffix=".h264", delete=False) as tmp_out:
        output_file = tmp_out.name

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "image2",
        "-i",
        input_file,
        "-vf",
        "format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-tune",
        "zerolatency",
        "-profile:v",
        "baseline",
        "-level",
        "3.0",
        "-x264-params",
        "cabac=0:ref=1:deblock=0:0:0:analyse=0:0:me=dia:subme=0:keyint=24:keyint_min=2:scenecut=0:bframes=0:mbtree=0",
        "-crf",
        "25",
        "-pix_fmt",
        "yuv420p",
        "-frames:v",
        "1",
        "-f",
        "h264",
        output_file,
    ]

    subprocess.run(cmd, capture_output=True)

    with open(output_file, "rb") as f:
        h264_data = f.read()

    try:
        os.unlink(input_file)
        os.unlink(output_file)
    except:
        pass

    return h264_data


def load_background(image_path: str, mode: str = "fill") -> Image.Image | None:
    """Load and resize image to 480x480 based on mode.
    
    Args:
        image_path: Path to image file (PNG, JPG, etc.)
        mode: Scaling mode - "stretch" (distort), "fit" (letterbox), or "fill" (crop)
        
    Returns:
        PIL Image or None if loading fails
    """
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")

            lcd_width, lcd_height = DISPLAY_SIZE

            if mode == "stretch":
                # Stretch to exact size
                img = img.resize((lcd_width, lcd_height), Image.Resampling.LANCZOS)

            elif mode == "fit":
                # Fit inside, letterbox with black
                img.thumbnail((lcd_width, lcd_height), Image.Resampling.LANCZOS)
                new_img = Image.new("RGB", (lcd_width, lcd_height), (0, 0, 0))
                x = (lcd_width - img.width) // 2
                y = (lcd_height - img.height) // 2
                new_img.paste(img, (x, y))
                img = new_img

            elif mode == "fill":
                # Crop to fill (may crop edges)
                img.thumbnail((lcd_width, lcd_height), Image.Resampling.LANCZOS)
                if img.width < lcd_width or img.height < lcd_height:
                    # If smaller, stretch to fill
                    img = img.resize((lcd_width, lcd_height), Image.Resampling.LANCZOS)
                else:
                    # Crop to exact size
                    left = (img.width - lcd_width) // 2
                    top = (img.height - lcd_height) // 2
                    right = left + lcd_width
                    bottom = top + lcd_height
                    img = img.crop((left, top, right, bottom))

            return img
    except Exception as e:
        print(f"❌ Error loading background '{image_path}': {e}")
        return None


def _find_font(pattern: str) -> str | None:
    """Find system font using fontconfig.
    
    Args:
        pattern: fontconfig pattern string (e.g., "NotoSansMono:weight=bold")
        
    Returns:
        str: Path to font file, or None if not found
    """
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", pattern], capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _get_system_fonts() -> Dict[str, Any]:
    """Get the best available system fonts for rendering.
    
    Returns:
        dict: Maps font type to file path or None
    """
    # NotoSansMono is best for clock (fixed-width digits don't jump)
    mono_font = _find_font("NotoSansMono:weight=bold")
    sans_font = _find_font("NotoSans:weight=bold")

    font_path = mono_font or sans_font
    
    return {
        "path": font_path,
        "available": font_path is not None,
    }


def _load_fonts(font_path: str | None) -> Dict[str, Any]:
    """Load TrueType fonts at specified sizes.
    
    Args:
        font_path: Path to TrueType font file
        
    Returns:
        dict: Maps font name to ImageFont object
    """
    fonts = {}
    try:
        if font_path and os.path.exists(font_path):
            fonts["time"] = ImageFont.truetype(font_path, FONT_SIZES["time"])
            fonts["cpu"] = ImageFont.truetype(font_path, FONT_SIZES["cpu"])
            fonts["date"] = ImageFont.truetype(font_path, FONT_SIZES["date"])
        else:
            raise FileNotFoundError(f"Font not found: {font_path}")
    except Exception as e:
        print(f"Warning: Font loading failed: {e}")
        fonts["time"] = fonts["cpu"] = fonts["date"] = ImageFont.load_default()
    
    return fonts


def _get_cpu_metrics() -> Tuple[str, str]:
    """Get CPU temperature and usage.
    
    Returns:
        tuple: (cpu_temp_str, cpu_percent_str)
    """
    cpu_temp = "N/A"
    try:
        temps = psutil.sensors_temperatures()
        for sensor_name in TEMP_SENSORS:
            if sensor_name in temps:
                cpu_temp = f"{int(temps[sensor_name][0].current)}°C"
                break
    except:
        pass

    cpu_percent = f"{int(psutil.cpu_percent(interval=0))}%"
    return cpu_temp, cpu_percent


def create_frame(bg_image: Image.Image | None = None, show_overlay: bool = True, overlay_opacity: int = 180) -> Image.Image:
    """Create a display frame with optional overlay.
    
    Args:
        bg_image: PIL Image to use as background (480x480 RGB)
        show_overlay: Whether to draw time/date/CPU overlay
        overlay_opacity: Opacity of overlay background (0-255)
        
    Returns:
        PIL Image: 480x480 RGB image ready for display
    """
    # Start with background or solid dark theme
    if bg_image:
        img = bg_image.copy()
    else:
        # Dark gaming theme fallback
        img = Image.new("RGB", DISPLAY_SIZE, color=DEFAULT_DARK_BG)
        draw = ImageDraw.Draw(img)
        draw.rectangle([40, 40, 440, 440], fill=DEFAULT_DARK_RECT)

    if not show_overlay:
        return img

    # Draw overlay if needed
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Get system fonts
    font_info = _get_system_fonts()
    fonts = _load_fonts(font_info["path"])

    # Get CPU metrics
    cpu_temp, cpu_percent = _get_cpu_metrics()

    # Get current time/date
    now = datetime.now()

    # Left - CPU temperature (cyan)
    draw.text(TEXT_POSITIONS["cpu_temp"], cpu_temp, fill=COLOR_CYAN, font=fonts["cpu"])

    # Right - CPU usage (orange)
    bbox = draw.textbbox((0, 0), cpu_percent, font=fonts["cpu"])
    tw = bbox[2] - bbox[0]
    draw.text(
        (420 - tw, TEXT_POSITIONS["cpu_usage"][1]),
        cpu_percent,
        fill=COLOR_ORANGE,
        font=fonts["cpu"],
    )

    # Time (bright cyan/green)
    time_text = now.strftime("%H:%M:%S")
    bbox = draw.textbbox((0, 0), time_text, font=fonts["time"])
    tw = bbox[2] - bbox[0]
    draw.text(
        (240 - tw // 2, TEXT_POSITIONS["time"][1]),
        time_text,
        fill=COLOR_BRIGHT_CYAN,
        font=fonts["time"],
    )

    # Date (muted gray)
    date_text = now.strftime("%d.%m.%Y")
    bbox = draw.textbbox((0, 0), date_text, font=fonts["date"])
    tw = bbox[2] - bbox[0]
    draw.text(
        (240 - tw // 2, TEXT_POSITIONS["date"][1]),
        date_text,
        fill=COLOR_GRAY,
        font=fonts["date"],
    )

    return img
