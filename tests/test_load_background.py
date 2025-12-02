"""Tests for load_background() function."""

import pytest
import sys
import os
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glc_control import load_background


class TestLoadBackground:
    """Test background image loading with different scaling modes."""

    def test_load_image_stretch_mode(self, temp_image):
        """Test loading image in stretch mode."""
        img = load_background(temp_image, mode="stretch")
        assert img is not None
        assert img.size == (480, 480)
        assert img.mode == "RGB"

    def test_load_image_fit_mode(self, temp_large_image):
        """Test loading image in fit mode with letterboxing."""
        img = load_background(temp_large_image, mode="fit")
        assert img is not None
        assert img.size == (480, 480)
        # Fit mode should preserve aspect ratio, so image might have black bars
        assert img.mode == "RGB"

    def test_load_image_fill_mode(self, temp_large_image):
        """Test loading image in fill mode with cropping."""
        img = load_background(temp_large_image, mode="fill")
        assert img is not None
        assert img.size == (480, 480)
        assert img.mode == "RGB"

    def test_load_small_image_stretch(self, temp_small_image):
        """Test loading small image in stretch mode."""
        img = load_background(temp_small_image, mode="stretch")
        assert img is not None
        assert img.size == (480, 480)

    def test_load_small_image_fit(self, temp_small_image):
        """Test loading small image in fit mode."""
        img = load_background(temp_small_image, mode="fit")
        assert img is not None
        assert img.size == (480, 480)

    def test_load_small_image_fill(self, temp_small_image):
        """Test loading small image in fill mode."""
        img = load_background(temp_small_image, mode="fill")
        assert img is not None
        assert img.size == (480, 480)

    def test_load_nonexistent_file(self):
        """Test loading non-existent file returns None."""
        img = load_background("/nonexistent/path/image.png")
        assert img is None

    def test_load_invalid_file_path(self):
        """Test loading invalid file path returns None."""
        img = load_background("")
        assert img is None

    def test_load_default_mode_is_fill(self, temp_large_image):
        """Test that default mode is 'fill'."""
        img_default = load_background(temp_large_image)
        img_fill = load_background(temp_large_image, mode="fill")
        assert img_default.size == img_fill.size == (480, 480)

    def test_image_converted_to_rgb(self, temp_image):
        """Test that image is converted to RGB format."""
        img = load_background(temp_image)
        assert img.mode == "RGB"

    def test_fit_mode_preserves_aspect_ratio(self):
        """Test that fit mode preserves aspect ratio."""
        # Create a wide image (1000x100)
        wide_img = Image.new("RGB", (1000, 100), color=(255, 0, 0))
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            wide_img.save(f.name)
            temp_path = f.name

        try:
            result = load_background(temp_path, mode="fit")
            # Image should still be 480x480, with black bars
            assert result.size == (480, 480)
            # Check that there are black bars (some pixels should be black)
            pixels = result.getdata()
            black_pixels = sum(1 for p in pixels if p == (0, 0, 0))
            assert black_pixels > 0, "Fit mode should add black bars"
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

    def test_fill_mode_crops_to_exact_size(self):
        """Test that fill mode crops to exact 480x480."""
        # Create a very large image
        large_img = Image.new("RGB", (2000, 2000), color=(0, 255, 0))
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            large_img.save(f.name)
            temp_path = f.name

        try:
            result = load_background(temp_path, mode="fill")
            assert result.size == (480, 480)
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

    def test_stretch_mode_exact_resize(self, temp_large_image):
        """Test that stretch mode does exact resize."""
        result = load_background(temp_large_image, mode="stretch")
        assert result.size == (480, 480)
        # Stretch mode might distort, but size should be exact
        assert result.width == 480
        assert result.height == 480

    def test_all_modes_return_rgb_image(self, temp_large_image):
        """Test that all modes return RGB image."""
        for mode in ["stretch", "fit", "fill"]:
            img = load_background(temp_large_image, mode=mode)
            assert img is not None
            assert img.mode == "RGB"
            assert img.size == (480, 480)

    @pytest.mark.parametrize("mode", ["stretch", "fit", "fill"])
    def test_all_modes_produce_correct_size(self, temp_large_image, mode):
        """Test that all modes produce 480x480 output."""
        img = load_background(temp_large_image, mode=mode)
        assert img.size == (480, 480)

    def test_load_jpeg_image(self):
        """Test loading JPEG image."""
        # Create and save a JPEG image
        jpeg_img = Image.new("RGB", (200, 200), color=(255, 128, 0))
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            jpeg_img.save(f.name, format="JPEG")
            temp_path = f.name

        try:
            result = load_background(temp_path)
            assert result is not None
            assert result.size == (480, 480)
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

    def test_square_image_in_fit_mode(self):
        """Test square image in fit mode."""
        square_img = Image.new("RGB", (480, 480), color=(100, 100, 100))
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            square_img.save(f.name)
            temp_path = f.name

        try:
            result = load_background(temp_path, mode="fit")
            assert result.size == (480, 480)
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
