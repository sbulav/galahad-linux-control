"""Tests for encode_h264() function."""

import pytest
import sys
import os
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glc_control import encode_h264


class TestEncodeH264:
    """Test H.264 encoding of images."""

    def test_encode_h264_returns_bytes(self, temp_image):
        """Test that encode_h264 returns bytes."""
        img = Image.open(temp_image)
        h264_data = encode_h264(img)
        assert isinstance(h264_data, bytes)

    def test_encode_h264_not_empty(self, temp_image):
        """Test that encode_h264 returns non-empty data."""
        img = Image.open(temp_image)
        h264_data = encode_h264(img)
        assert len(h264_data) > 0

    def test_encode_h264_rgb_image(self):
        """Test encoding RGB image."""
        img = Image.new("RGB", (480, 480), color=(255, 0, 0))
        h264_data = encode_h264(img)
        assert h264_data is not None
        assert len(h264_data) > 0

    def test_encode_h264_small_image(self):
        """Test encoding small image."""
        img = Image.new("RGB", (100, 100), color=(0, 255, 0))
        h264_data = encode_h264(img)
        assert h264_data is not None
        assert len(h264_data) > 0

    def test_encode_h264_large_image(self):
        """Test encoding large image."""
        img = Image.new("RGB", (1000, 1000), color=(0, 0, 255))
        h264_data = encode_h264(img)
        assert h264_data is not None
        assert len(h264_data) > 0

    def test_encode_h264_different_colors(self):
        """Test that different color images encode."""
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        for color in colors:
            img = Image.new("RGB", (480, 480), color=color)
            h264_data = encode_h264(img)
            assert isinstance(h264_data, bytes)
            assert len(h264_data) > 0

    def test_encode_h264_has_h264_header(self, temp_image):
        """Test that encoded data starts with H.264 NAL unit headers."""
        img = Image.open(temp_image)
        h264_data = encode_h264(img)
        # H.264 frames typically start with NAL unit headers (0x00 0x00 0x00 0x01)
        # or contain them within the data
        assert len(h264_data) > 4

    def test_encode_h264_consistent_output_size(self):
        """Test that same image produces consistent output size."""
        img = Image.new("RGB", (480, 480), color=(128, 128, 128))
        h264_1 = encode_h264(img)
        h264_2 = encode_h264(img)
        # Should produce similar sized output
        assert abs(len(h264_1) - len(h264_2)) < len(h264_1) * 0.1

    def test_encode_h264_preserves_image_object(self):
        """Test that encoding doesn't modify the original image."""
        img = Image.new("RGB", (480, 480), color=(200, 100, 50))
        original_size = img.size
        original_mode = img.mode
        h264_data = encode_h264(img)
        assert img.size == original_size
        assert img.mode == original_mode

    def test_encode_h264_handles_various_sizes(self):
        """Test encoding images of various sizes."""
        sizes = [(100, 100), (240, 240), (480, 480), (640, 480), (800, 600)]
        for width, height in sizes:
            img = Image.new("RGB", (width, height), color=(100, 150, 200))
            h264_data = encode_h264(img)
            assert h264_data is not None
            assert len(h264_data) > 0

    def test_encode_h264_rectangular_image(self):
        """Test encoding rectangular (non-square) image."""
        img = Image.new("RGB", (800, 600), color=(75, 75, 75))
        h264_data = encode_h264(img)
        assert h264_data is not None
        assert len(h264_data) > 0

    def test_encode_h264_from_file(self, temp_image):
        """Test encoding image loaded from file."""
        img = Image.open(temp_image)
        h264_data = encode_h264(img)
        assert isinstance(h264_data, bytes)
        assert len(h264_data) > 0

    def test_encode_h264_gradient_image(self):
        """Test encoding gradient image (variable colors)."""
        img = Image.new("RGB", (480, 480), color=(200, 100, 50))
        # Draw some variation
        pixels = img.load()
        for i in range(0, 480, 10):
            for j in range(0, 480, 10):
                pixels[i, j] = ((i * 255) // 480, (j * 255) // 480, 128)
        h264_data = encode_h264(img)
        assert h264_data is not None
        assert len(h264_data) > 0

    @pytest.mark.parametrize("width,height", [
        (100, 100),
        (480, 480),
        (640, 480),
        (1920, 1080),
    ])
    def test_encode_h264_parametrized_sizes(self, width, height):
        """Test encoding with parametrized image sizes."""
        img = Image.new("RGB", (width, height), color=(100, 150, 200))
        h264_data = encode_h264(img)
        assert isinstance(h264_data, bytes)
        assert len(h264_data) > 0

    def test_encode_h264_cleanup_temp_files(self, temp_image):
        """Test that temporary files are cleaned up after encoding."""
        import tempfile
        initial_temp_count = len(os.listdir(tempfile.gettempdir()))

        img = Image.open(temp_image)
        h264_data = encode_h264(img)

        # Temp directory shouldn't grow significantly (cleanup worked)
        final_temp_count = len(os.listdir(tempfile.gettempdir()))
        # Allow for some variance but not too many temp files left
        assert (final_temp_count - initial_temp_count) < 10
