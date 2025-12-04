"""Preset modes for gaii-control display rendering."""

import random
import string
import math
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


class HeartbeatPreset(Preset):
    """Pulsing heartbeat visualization based on CPU load.
    
    Features:
    - Animated bar graph using Unicode block characters ▁▂▃▄▅▆▇█
    - Bar pulses from center outward based on CPU load
    - Color gradient: green (low) → yellow (mid) → red (high)
    - CPU percentage displayed in center
    - Smooth pulsing animation synchronized to load
    """
    
    def __init__(self, fps: float = 10.0):
        """Initialize Heartbeat preset.
        
        Args:
            fps: Frames per second for animation speed
        """
        super().__init__("heartbeat")
        self.fps = fps
        self.frame_count = 0
        
        # Display dimensions
        self.width, self.height = DISPLAY_SIZE
        
        # Block characters for visualization (8 levels)
        self.blocks = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
        
        # Number of bar segments (symmetric from center)
        self.segment_count = 16  # 16 segments total (8 on each side)
        
        # Font setup
        self.bar_font = self._load_bar_font()
        self.cpu_font = self._load_cpu_font()
        
        # Color definitions
        self.bg_color = (0, 0, 0)  # Black background
        
        # CPU load tracking (smoothed)
        self.cpu_history: List[float] = []
        self.cpu_history_size = 5
        self.current_cpu = 0.0
    
    def _load_bar_font(self) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
        """Load large monospace font for bar characters.
        
        Returns:
            ImageFont: Loaded font or default font
        """
        try:
            result = subprocess.run(
                ["fc-match", "-f", "%{file}", "NotoSansMono"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                font_path = result.stdout.strip()
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, 80)
        except Exception:
            pass
        
        return ImageFont.load_default()
    
    def _load_cpu_font(self) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
        """Load font for CPU percentage display.
        
        Returns:
            ImageFont: Loaded font or default font
        """
        try:
            result = subprocess.run(
                ["fc-match", "-f", "%{file}", "NotoSansMono:weight=bold"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                font_path = result.stdout.strip()
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, 48)
        except Exception:
            pass
        
        return ImageFont.load_default()
    
    def _get_cpu_load(self) -> float:
        """Get current CPU load percentage (smoothed).
        
        Returns:
            float: CPU load 0-100
        """
        try:
            # Non-blocking CPU percent reading
            cpu = psutil.cpu_percent(interval=0)
            
            # Add to history for smoothing
            self.cpu_history.append(cpu)
            if len(self.cpu_history) > self.cpu_history_size:
                self.cpu_history.pop(0)
            
            # Return smoothed average
            return sum(self.cpu_history) / len(self.cpu_history)
        except Exception:
            return 0.0
    
    def _get_color_for_load(self, load: float) -> Tuple[int, int, int]:
        """Get color based on CPU load percentage.
        
        Args:
            load: CPU load 0-100
            
        Returns:
            tuple: (R, G, B) color values
        """
        if load < 50:
            # Green zone (0-50%)
            # Interpolate from bright green to yellow-green
            ratio = load / 50.0
            r = int(ratio * 100)
            g = 255
            b = 0
            return (r, g, b)
        elif load < 75:
            # Yellow zone (50-75%)
            # Interpolate from yellow-green to orange
            ratio = (load - 50) / 25.0
            r = int(100 + ratio * 155)
            g = 255
            b = 0
            return (r, g, b)
        else:
            # Red zone (75-100%)
            # Interpolate from orange to bright red
            ratio = (load - 75) / 25.0
            r = 255
            g = int(255 * (1 - ratio))
            b = 0
            return (r, g, b)
    
    def _calculate_pulse_intensity(self, segment_idx: int, cpu_load: float) -> float:
        """Calculate pulse intensity for a given segment.
        
        Creates a pulsing wave effect that emanates from center.
        
        Args:
            segment_idx: Segment index (0 = center, higher = edge)
            cpu_load: Current CPU load 0-100
            
        Returns:
            float: Intensity 0-1 for this segment
        """
        # Base intensity from CPU load (boosted so 80%+ CPU can reach full █)
        base_intensity = min(1.2, cpu_load / 80.0)  # Over 1.0 to compensate for wave/center factors
        
        # Create pulsing sine wave (frequency based on CPU load)
        pulse_speed = 2.0 + (cpu_load / 100.0) * 4.0  # Faster pulse with higher load
        pulse_phase = (self.frame_count / self.fps) * pulse_speed
        
        # Wave propagates OUTWARD from center (positive offset for outward motion)
        wave_offset = segment_idx * 0.4
        pulse_wave = (math.sin(pulse_phase + wave_offset) + 1.0) / 2.0  # 0-1 range
        
        # Center segments are STRONGER (heartbeat emanates from center)
        # Closer to center = taller bars
        center_boost = 1.0 - (segment_idx / (self.segment_count / 2)) * 0.4
        
        intensity = base_intensity * pulse_wave * center_boost
        return max(0.0, min(1.0, intensity))
    
    def render(self) -> Image.Image:
        """Render a frame with pulsing heartbeat CPU visualization.
        
        Returns:
            PIL Image: 480x480 RGB frame
        """
        # Create black background
        img = Image.new("RGB", DISPLAY_SIZE, color=self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Get current CPU load
        cpu_load = self._get_cpu_load()
        self.current_cpu = cpu_load
        
        # Get color for current load
        bar_color = self._get_color_for_load(cpu_load)
        
        # Calculate bar layout
        # Draw segments from center outward (symmetric)
        half_segments = self.segment_count // 2
        
        # Build bar string with block characters
        bar_chars = []
        bar_chars.append('|')  # Left bracket
        
        # Left side (reverse order - tallest in center)
        for i in range(half_segments - 1, -1, -1):
            intensity = self._calculate_pulse_intensity(i, cpu_load)
            block_idx = int(intensity * (len(self.blocks) - 1))
            bar_chars.append(self.blocks[block_idx])
        
        # Right side (mirror of left)
        for i in range(half_segments):
            intensity = self._calculate_pulse_intensity(i, cpu_load)
            block_idx = int(intensity * (len(self.blocks) - 1))
            bar_chars.append(self.blocks[block_idx])
        
        bar_chars.append('|')  # Right bracket
        bar_string = ''.join(bar_chars)
        
        # Draw the bar
        # Center it horizontally
        bbox = draw.textbbox((0, 0), bar_string, font=self.bar_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        bar_x = (self.width - text_width) // 2
        bar_y = (self.height - text_height) // 2 + 40  # Slightly below center
        
        draw.text(
            (bar_x, bar_y),
            bar_string,
            fill=bar_color,
            font=self.bar_font,
        )
        
        # Draw CPU percentage in center (above bar)
        cpu_text = f"{int(cpu_load)}%"
        cpu_bbox = draw.textbbox((0, 0), cpu_text, font=self.cpu_font)
        cpu_width = cpu_bbox[2] - cpu_bbox[0]
        cpu_height = cpu_bbox[3] - cpu_bbox[1]
        
        cpu_x = (self.width - cpu_width) // 2
        cpu_y = (self.height - cpu_height) // 2 - 80  # Above bar
        
        # Draw semi-transparent background for CPU text
        padding = 15
        bg_box = [
            cpu_x - padding,
            cpu_y - padding,
            cpu_x + cpu_width + padding,
            cpu_y + cpu_height + padding,
        ]
        
        # Slightly tinted background box
        draw.rectangle(bg_box, fill=(20, 20, 20))
        
        # Draw CPU percentage text
        draw.text(
            (cpu_x, cpu_y),
            cpu_text,
            fill=bar_color,
            font=self.cpu_font,
        )
        
        # Draw label
        label_text = "CPU LOAD"
        label_font = self._load_cpu_font()  # Reuse same font
        
        # Make label smaller by trying a smaller size
        try:
            result = subprocess.run(
                ["fc-match", "-f", "%{file}", "NotoSansMono"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                font_path = result.stdout.strip()
                if os.path.exists(font_path):
                    label_font = ImageFont.truetype(font_path, 20)
        except Exception:
            pass
        
        label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
        label_width = label_bbox[2] - label_bbox[0]
        label_x = (self.width - label_width) // 2
        label_y = cpu_y - 40
        
        # Draw label with dimmer color
        dim_color = tuple(int(c * 0.5) for c in bar_color)
        draw.text(
            (label_x, label_y),
            label_text,
            fill=dim_color,
            font=label_font,
        )
        
        self.frame_count += 1
        return img
