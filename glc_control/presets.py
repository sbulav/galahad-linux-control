"""Preset modes for gaii-control display rendering."""

import random
import string
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Any, List, Union
from PIL import Image, ImageDraw, ImageFont
import psutil
import subprocess
import os

from .config import DISPLAY_SIZE, TEMP_SENSORS


class Preset(ABC):
    """Abstract base class for display presets."""
    
    def __init__(self, name: str):
        """Initialize preset.
        
        Args:
            name: Name identifier for the preset
        """
        self.name = name
    
    @abstractmethod
    def render(self) -> Image.Image:
        """Render a frame for this preset.
        
        Returns:
            PIL Image: 480x480 RGB image ready for display
        """
        pass


class MatrixPreset(Preset):
    """Matrix-style falling characters with CPU temperature display.
    
    Features:
    - Green monochromatic color scheme
    - Falling letters/numbers animation (bottom-to-top)
    - CPU temperature displayed in center
    - Smooth animation between frames
    """
    
    def __init__(self, fps: float = 10.0):
        """Initialize Matrix preset.
        
        Args:
            fps: Frames per second for animation speed
        """
        super().__init__("matrix")
        self.fps = fps
        self.frame_count = 0
        
        # Display dimensions
        self.width, self.height = DISPLAY_SIZE
        
        # Matrix configuration
        self.char_pool = string.ascii_letters + string.digits
        self.col_count = self.width // 10  # ~48 columns for 480px width
        self.cell_height = 15  # Height of each character cell
        
        # Initialize column states (y position of falling character)
        self.columns: Dict[int, Dict[str, Any]] = {}
        for col in range(self.col_count):
            self.columns[col] = {
                'y': random.randint(-200, 0),  # Start above screen
                'char': random.choice(self.char_pool),
                'speed': random.uniform(1.5, 3.0),  # Pixels per frame
                'brightness': 255,  # 0-255, fades as it falls
                'trail_length': random.randint(5, 15),  # Length of fade trail
            }
        
        # Font setup - load once and cache
        self.font = self._load_font()
        self.temp_font = self._load_temp_font()  # Cache temperature font
        
        # Color palette - shades of green
        self.colors = {
            'bright': (0, 255, 0),      # Bright green - leading edge
            'mid': (0, 200, 0),         # Mid green
            'dim': (0, 100, 0),         # Dim green
            'very_dim': (0, 50, 0),     # Very dim green
            'bg': (0, 0, 0),            # Black background
        }
    
    def _load_font(self) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
        """Load or fall back to default font.
        
        Returns:
            ImageFont: Loaded font or default font
        """
        try:
            # Try to find monospace font
            result = subprocess.run(
                ["fc-match", "-f", "%{file}", "NotoSansMono"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                font_path = result.stdout.strip()
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, 12)
        except Exception:
            pass
        
        # Fall back to default font
        return ImageFont.load_default()
    
    def _load_temp_font(self) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
        """Load large font for temperature display (cached at init).
        
        Returns:
            ImageFont: Loaded font or default font
        """
        try:
            result = subprocess.run(
                ["fc-match", "-f", "%{file}", "NotoSansMono:weight=bold"],
                capture_output=True,
                text=True,
            )
            font_path = result.stdout.strip() if result.returncode == 0 else None
            if font_path and os.path.exists(font_path):
                return ImageFont.truetype(font_path, 60)
        except Exception:
            pass
        
        # Fall back to small font
        return self.font
    
    def _get_cpu_temp(self) -> str:
        """Get current CPU temperature.
        
        Returns:
            str: CPU temperature string (e.g., "45°C") or "N/A"
        """
        try:
            temps = psutil.sensors_temperatures()
            for sensor_name in TEMP_SENSORS:
                if sensor_name in temps:
                    return f"{int(temps[sensor_name][0].current)}°C"
        except Exception:
            pass
        return "N/A"
    
    def _interpolate_color(self, brightness: float) -> Tuple[int, int, int]:
        """Interpolate color based on brightness/position in trail.
        
        Args:
            brightness: Value 0-1 indicating trail position (1=bright, 0=dim)
            
        Returns:
            tuple: (R, G, B) color values
        """
        if brightness > 0.75:
            return self.colors['bright']
        elif brightness > 0.5:
            return self.colors['mid']
        elif brightness > 0.25:
            return self.colors['dim']
        else:
            return self.colors['very_dim']
    
    def render(self) -> Image.Image:
        """Render a frame with falling matrix characters and CPU temp.
        
        Returns:
            PIL Image: 480x480 RGB frame
        """
        # Create black background
        img = Image.new("RGB", DISPLAY_SIZE, color=self.colors['bg'])
        draw = ImageDraw.Draw(img)
        
        # Update and draw columns
        for col_idx in range(self.col_count):
            col = self.columns[col_idx]
            
            # Update position
            col['y'] += col['speed']
            
            # Reset column if it falls off screen
            if col['y'] > self.height + 100:
                col['y'] = -200
                col['char'] = random.choice(self.char_pool)
                col['speed'] = random.uniform(1.5, 3.0)
            
            # Draw character trail
            trail_length = col['trail_length']
            for i in range(trail_length):
                y_pos = col['y'] - (i * self.cell_height)
                
                # Only draw if visible on screen
                if -20 < y_pos < self.height + 20:
                    # Calculate brightness for this trail segment
                    brightness = 1.0 - (i / trail_length)
                    color = self._interpolate_color(brightness)
                    
                    # Draw character
                    x_pos = col_idx * 10 + 2
                    try:
                        draw.text(
                            (x_pos, int(y_pos)),
                            col['char'],
                            fill=color,
                            font=self.font,
                        )
                    except Exception:
                        pass
        
        # Draw CPU temperature in center (using cached font)
        cpu_temp = self._get_cpu_temp()
        
        # Get text bounding box for centering
        bbox = draw.textbbox((0, 0), cpu_temp, font=self.temp_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Draw semi-transparent background for temperature
        padding = 10
        bg_box = [
            self.width // 2 - text_width // 2 - padding,
            self.height // 2 - text_height // 2 - padding,
            self.width // 2 + text_width // 2 + padding,
            self.height // 2 + text_height // 2 + padding,
        ]
        
        # Create overlay for background box
        overlay = Image.new("RGB", DISPLAY_SIZE, color=self.colors['bg'])
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(bg_box, fill=(0, 30, 0))
        
        # Blend overlay with main image
        img = Image.blend(img, overlay, 0.3)
        draw = ImageDraw.Draw(img)
        
        # Draw temperature text in bright green
        draw.text(
            (self.width // 2 - text_width // 2, self.height // 2 - text_height // 2),
            cpu_temp,
            fill=self.colors['bright'],
            font=self.temp_font,
        )
        
        self.frame_count += 1
        return img
