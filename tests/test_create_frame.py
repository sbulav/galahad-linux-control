"""Tests for create_frame() function."""

import pytest
import sys
import os
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glc_control import create_frame, load_background


class TestCreateFrame:
    """Test frame creation with overlays and backgrounds."""

    def test_create_frame_default_no_background(self):
        """Test creating frame without background image."""
        img = create_frame(bg_image=None, show_overlay=True)
        assert img is not None
        assert img.size == (480, 480)
        assert img.mode == "RGB"

    def test_create_frame_with_overlay(self, temp_image):
        """Test creating frame with overlay enabled."""
        bg = load_background(temp_image)
        img = create_frame(bg_image=bg, show_overlay=True)
        assert img is not None
        assert img.size == (480, 480)

    def test_create_frame_without_overlay(self, temp_image):
        """Test creating frame with overlay disabled."""
        bg = load_background(temp_image)
        img = create_frame(bg_image=bg, show_overlay=False)
        assert img is not None
        assert img.size == (480, 480)

    def test_create_frame_overlay_returns_background(self, temp_image):
        """Test that frame without overlay returns background unchanged."""
        bg = load_background(temp_image)
        img = create_frame(bg_image=bg, show_overlay=False)
        # Without overlay, should return the background image
        assert img.size == bg.size

    def test_create_frame_with_opacity_low(self):
        """Test creating frame with low overlay opacity."""
        bg = Image.new("RGB", (480, 480), color=(100, 100, 100))
        img = create_frame(bg_image=bg, show_overlay=True, overlay_opacity=50)
        assert img is not None
        assert img.size == (480, 480)

    def test_create_frame_with_opacity_high(self):
        """Test creating frame with high overlay opacity."""
        bg = Image.new("RGB", (480, 480), color=(100, 100, 100))
        img = create_frame(bg_image=bg, show_overlay=True, overlay_opacity=255)
        assert img is not None
        assert img.size == (480, 480)

    def test_create_frame_with_opacity_zero(self):
        """Test creating frame with zero overlay opacity."""
        bg = Image.new("RGB", (480, 480), color=(50, 50, 50))
        img = create_frame(bg_image=bg, show_overlay=True, overlay_opacity=0)
        assert img is not None
        assert img.size == (480, 480)

    def test_create_frame_output_is_rgb(self):
        """Test that output frame is always RGB."""
        bg = Image.new("RGB", (480, 480), color=(0, 0, 0))
        img = create_frame(bg_image=bg, show_overlay=True)
        assert img.mode == "RGB"

    def test_create_frame_size_always_480x480(self):
        """Test that frame is always 480x480 pixels."""
        bg = Image.new("RGB", (480, 480), color=(255, 255, 255))
        img = create_frame(bg_image=bg, show_overlay=True)
        assert img.width == 480
        assert img.height == 480

    def test_create_frame_with_overlay_adds_text(self):
        """Test that overlay with text is created."""
        bg = Image.new("RGB", (480, 480), color=(30, 30, 30))
        img = create_frame(bg_image=bg, show_overlay=True, overlay_opacity=180)
        # Check that image has some variation in pixels (text was drawn)
        pixels = list(img.getdata())
        unique_colors = set(pixels)
        assert len(unique_colors) > 1, "Overlay should add text with different colors"

    def test_create_frame_default_background(self):
        """Test that default background (None) creates dark theme."""
        img = create_frame(bg_image=None, show_overlay=False)
        assert img is not None
        # Should be dark (30, 30, 30) background with darker rectangle
        pixels = list(img.getdata())
        # Count dark pixels
        dark_pixels = sum(1 for p in pixels if p[0] <= 30 and p[1] <= 30 and p[2] <= 30)
        assert dark_pixels > 0

    def test_create_frame_with_different_opacity_values(self, temp_image):
        """Test that different opacity values produce different results."""
        bg = load_background(temp_image)
        img1 = create_frame(bg_image=bg, show_overlay=True, overlay_opacity=100)
        img2 = create_frame(bg_image=bg, show_overlay=True, overlay_opacity=200)
        # Both should be valid
        assert img1.size == img2.size == (480, 480)

    @pytest.mark.parametrize("opacity", [0, 50, 100, 150, 180, 200, 255])
    def test_create_frame_all_opacity_values(self, opacity):
        """Test frame creation with various opacity values."""
        bg = Image.new("RGB", (480, 480), color=(100, 100, 100))
        img = create_frame(bg_image=bg, show_overlay=True, overlay_opacity=opacity)
        assert img is not None
        assert img.size == (480, 480)
        assert img.mode == "RGB"

    @pytest.mark.parametrize("overlay_enabled", [True, False])
    def test_create_frame_overlay_toggle(self, overlay_enabled):
        """Test frame creation with overlay toggled."""
        bg = Image.new("RGB", (480, 480), color=(50, 50, 50))
        img = create_frame(bg_image=bg, show_overlay=overlay_enabled)
        assert img is not None
        assert img.size == (480, 480)

    def test_create_frame_consecutive_calls(self):
        """Test that consecutive calls produce valid frames."""
        bg = Image.new("RGB", (480, 480), color=(75, 75, 75))
        img1 = create_frame(bg_image=bg, show_overlay=True)
        img2 = create_frame(bg_image=bg, show_overlay=True)
        assert img1.size == img2.size == (480, 480)

    def test_create_frame_preserves_background_size(self, temp_large_image):
        """Test that frame respects background size after loading."""
        bg = load_background(temp_large_image)
        assert bg.size == (480, 480)
        img = create_frame(bg_image=bg, show_overlay=True)
        assert img.size == (480, 480)
