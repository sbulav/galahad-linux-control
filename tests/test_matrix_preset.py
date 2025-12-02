"""Tests for MatrixPreset rendering."""

import pytest
from PIL import Image
from gaii_control.presets import MatrixPreset, Preset


class TestPresetBase:
    """Test base Preset class."""

    def test_preset_is_abstract(self):
        """Test that Preset cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Preset("test")


class TestMatrixPreset:
    """Test MatrixPreset rendering and animation."""

    def test_matrix_preset_initialization(self):
        """Test MatrixPreset can be initialized with custom FPS."""
        preset = MatrixPreset(fps=15.0)
        assert preset.name == "matrix"
        assert preset.fps == 15.0
        assert preset.width == 480
        assert preset.height == 480

    def test_matrix_preset_default_fps(self):
        """Test MatrixPreset uses default FPS if not specified."""
        preset = MatrixPreset()
        assert preset.fps == 10.0

    def test_matrix_render_returns_image(self):
        """Test that render() returns a valid PIL Image."""
        preset = MatrixPreset()
        img = preset.render()
        assert isinstance(img, Image.Image)
        assert img.size == (480, 480)
        assert img.mode == "RGB"

    def test_matrix_render_multiple_frames(self):
        """Test that render() produces consistent frames."""
        preset = MatrixPreset()
        frames = [preset.render() for _ in range(5)]
        
        for frame in frames:
            assert frame.size == (480, 480)
            assert frame.mode == "RGB"

    def test_matrix_color_scheme_green(self):
        """Test that matrix preset uses green color scheme."""
        preset = MatrixPreset()
        img = preset.render()
        
        pixels = list(img.getdata())
        
        # Count green vs black pixels
        green_count = 0
        black_count = 0
        
        for r, g, b in pixels:
            # Green: high G, low R and B
            if g > 50 and r < 100 and b < 100:
                green_count += 1
            # Black: all channels low
            elif r < 30 and g < 30 and b < 30:
                black_count += 1
        
        # Should have some green pixels for the falling characters
        assert green_count > 50, f"Expected > 100 green pixels, got {green_count}"
        
        # Most pixels should be black background
        assert black_count > len(pixels) * 0.5, "Expected > 50% black background"

    def test_matrix_animation_state_changes(self):
        """Test that animation state progresses between frames."""
        preset = MatrixPreset(fps=20.0)  # Faster FPS for more visible changes
        
        # Get initial positions
        initial_positions = {i: col['y'] for i, col in preset.columns.items()}
        
        # Render multiple times to advance animation
        for _ in range(10):
            preset.render()
        
        # Get final positions
        final_positions = {i: col['y'] for i, col in preset.columns.items()}
        
        # At least some columns should have changed position
        changed = sum(1 for i in initial_positions 
                     if initial_positions[i] != final_positions[i])
        
        assert changed > 0, "Animation positions did not change"

    def test_matrix_cpu_temperature_reading(self):
        """Test that CPU temperature can be read."""
        preset = MatrixPreset()
        temp = preset._get_cpu_temp()
        
        # Should be either a valid temperature or N/A
        assert temp == "N/A" or (
            temp.endswith("°C") and int(temp[:-2]) > 0
        ), f"Invalid temperature format: {temp}"

    def test_matrix_color_interpolation(self):
        """Test color interpolation for trail effect."""
        preset = MatrixPreset()
        
        # Test brightness levels
        color_bright = preset._interpolate_color(0.9)
        color_mid = preset._interpolate_color(0.5)
        color_dim = preset._interpolate_color(0.2)
        
        # All should be green shades
        for r, g, b in [color_bright, color_mid, color_dim]:
            assert g > r and g > b, f"Color should be green-ish: ({r}, {g}, {b})"
            assert 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255

    def test_matrix_column_reset(self):
        """Test that columns reset when falling off screen."""
        preset = MatrixPreset(fps=10.0)
        
        # Force a column far below the screen to trigger reset
        preset.columns[0]['y'] = 1000
        
        # Render to trigger reset (which happens when y > height + 100 = 580)
        preset.render()
        
        # After reset, column should be back at top (between -200 and 0)
        assert -200 <= preset.columns[0]['y'] <= 0, \
            f"Column should reset to top range [-200, 0], got {preset.columns[0]['y']}"

    def test_matrix_frame_count_increments(self):
        """Test that frame counter increments."""
        preset = MatrixPreset()
        
        initial_count = preset.frame_count
        preset.render()
        assert preset.frame_count == initial_count + 1
        
        preset.render()
        assert preset.frame_count == initial_count + 2

    def test_matrix_preset_with_different_fps(self):
        """Test MatrixPreset renders correctly at different FPS values."""
        for fps in [5, 10, 15, 30]:
            preset = MatrixPreset(fps=fps)
            img = preset.render()
            assert img.size == (480, 480), f"Failed for fps={fps}"
            assert img.mode == "RGB", f"Failed for fps={fps}"
