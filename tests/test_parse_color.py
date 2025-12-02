"""Tests for parse_color() function."""

import pytest
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gaii_control import parse_color


class TestParseColor:
    """Test color parsing in hex, RGB, and named color formats."""

    # ========== Named Color Tests ==========
    def test_named_color_red(self):
        """Test named color 'red'."""
        result = parse_color("red")
        assert result == (255, 0, 0)

    def test_named_color_blue(self):
        """Test named color 'blue'."""
        result = parse_color("blue")
        assert result == (0, 0, 255)

    def test_named_color_green(self):
        """Test named color 'green'."""
        result = parse_color("green")
        assert result == (0, 255, 0)

    def test_named_color_yellow(self):
        """Test named color 'yellow'."""
        result = parse_color("yellow")
        assert result == (255, 255, 0)

    def test_named_color_cyan(self):
        """Test named color 'cyan'."""
        result = parse_color("cyan")
        assert result == (0, 255, 255)

    def test_named_color_magenta(self):
        """Test named color 'magenta'."""
        result = parse_color("magenta")
        assert result == (255, 0, 255)

    def test_named_color_white(self):
        """Test named color 'white'."""
        result = parse_color("white")
        assert result == (255, 255, 255)

    def test_named_color_black(self):
        """Test named color 'black'."""
        result = parse_color("black")
        assert result == (0, 0, 0)

    def test_named_color_gray(self):
        """Test named color 'gray'."""
        result = parse_color("gray")
        assert result == (128, 128, 128)

    def test_named_color_grey(self):
        """Test named color 'grey' (alias for gray)."""
        result = parse_color("grey")
        assert result == (128, 128, 128)

    def test_named_color_bright_red(self):
        """Test named color 'bright_red'."""
        result = parse_color("bright_red")
        assert result == (255, 64, 64)

    def test_named_color_bright_green(self):
        """Test named color 'bright_green'."""
        result = parse_color("bright_green")
        assert result == (64, 255, 64)

    def test_named_color_bright_blue(self):
        """Test named color 'bright_blue'."""
        result = parse_color("bright_blue")
        assert result == (64, 64, 255)

    def test_named_color_bright_yellow(self):
        """Test named color 'bright_yellow'."""
        result = parse_color("bright_yellow")
        assert result == (255, 255, 64)

    def test_named_color_bright_cyan(self):
        """Test named color 'bright_cyan'."""
        result = parse_color("bright_cyan")
        assert result == (64, 255, 255)

    def test_named_color_bright_magenta(self):
        """Test named color 'bright_magenta'."""
        result = parse_color("bright_magenta")
        assert result == (255, 64, 255)

    def test_named_color_bright_white(self):
        """Test named color 'bright_white'."""
        result = parse_color("bright_white")
        assert result == (255, 255, 255)

    def test_named_color_case_insensitive_uppercase(self):
        """Test that color names are case-insensitive (uppercase)."""
        result = parse_color("BLUE")
        assert result == (0, 0, 255)

    def test_named_color_case_insensitive_mixed(self):
        """Test that color names are case-insensitive (mixed case)."""
        result = parse_color("BrIgHt_ReD")
        assert result == (255, 64, 64)

    def test_named_color_with_whitespace(self):
        """Test that whitespace around color name is trimmed."""
        result = parse_color("  red  ")
        assert result == (255, 0, 0)

    # ========== Hex Color Tests ==========
    def test_hex_color_with_hash(self):
        """Test hex color with # prefix."""
        result = parse_color("#FF0000")
        assert result == (255, 0, 0)

    def test_hex_color_without_hash(self):
        """Test hex color without # prefix."""
        result = parse_color("00FF00")
        assert result == (0, 255, 0)

    def test_hex_color_lowercase(self):
        """Test hex color in lowercase."""
        result = parse_color("#00ffcc")
        assert result == (0, 255, 204)

    def test_hex_color_mixed_case(self):
        """Test hex color in mixed case."""
        result = parse_color("#FfFfFf")
        assert result == (255, 255, 255)

    def test_hex_color_black(self):
        """Test hex color for black."""
        result = parse_color("#000000")
        assert result == (0, 0, 0)

    def test_hex_color_white(self):
        """Test hex color for white."""
        result = parse_color("FFFFFF")
        assert result == (255, 255, 255)

    def test_rgb_format_simple(self):
        """Test RGB comma-separated format."""
        result = parse_color("255,0,0")
        assert result == (255, 0, 0)

    def test_rgb_format_with_spaces(self):
        """Test RGB format with spaces around values."""
        result = parse_color("0, 255, 0")
        assert result == (0, 255, 0)

    def test_rgb_format_min_values(self):
        """Test RGB with minimum values."""
        result = parse_color("0,0,0")
        assert result == (0, 0, 0)

    def test_rgb_format_max_values(self):
        """Test RGB with maximum values."""
        result = parse_color("255,255,255")
        assert result == (255, 255, 255)

    def test_rgb_format_mixed_values(self):
        """Test RGB with mixed values."""
        result = parse_color("128, 64, 192")
        assert result == (128, 64, 192)

    def test_invalid_hex_short(self):
        """Test invalid hex color too short."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_color("#FFFF")

    def test_invalid_hex_long(self):
        """Test invalid hex color too long."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_color("#FFFFFFF")

    def test_invalid_hex_chars(self):
        """Test invalid hex characters."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_color("#GGGGGG")

    def test_invalid_rgb_too_many_values(self):
        """Test RGB with too many values."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_color("255,0,0,100")

    def test_invalid_rgb_too_few_values(self):
        """Test RGB with too few values."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_color("255,0")

    def test_invalid_rgb_out_of_range_high(self):
        """Test RGB with value > 255."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_color("256,0,0")

    def test_invalid_rgb_out_of_range_low(self):
        """Test RGB with negative value."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_color("-1,0,0")

    def test_invalid_rgb_non_numeric(self):
        """Test RGB with non-numeric values."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_color("abc,def,ghi")

    def test_invalid_format_mixed(self):
        """Test completely invalid format."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_color("not a color")

    def test_color_with_whitespace_trim(self):
        """Test that whitespace is trimmed."""
        result = parse_color("  #FF0000  ")
        assert result == (255, 0, 0)

    @pytest.mark.parametrize("color_input,expected", [
        # Named colors
        ("red", (255, 0, 0)),
        ("blue", (0, 0, 255)),
        ("green", (0, 255, 0)),
        ("yellow", (255, 255, 0)),
        ("cyan", (0, 255, 255)),
        ("magenta", (255, 0, 255)),
        ("white", (255, 255, 255)),
        ("black", (0, 0, 0)),
        ("gray", (128, 128, 128)),
        ("grey", (128, 128, 128)),
        ("bright_red", (255, 64, 64)),
        ("bright_green", (64, 255, 64)),
        ("bright_blue", (64, 64, 255)),
        ("BLUE", (0, 0, 255)),  # Case insensitive
        ("ReD", (255, 0, 0)),   # Case insensitive
        # Hex colors
        ("#FF0000", (255, 0, 0)),
        ("00FF00", (0, 255, 0)),
        ("0,0,255", (0, 0, 255)),
        ("#00FFC8", (0, 255, 200)),
        ("255, 255, 255", (255, 255, 255)),
    ])
    def test_valid_colors_parametrized(self, color_input, expected):
        """Test various valid color formats including named colors."""
        assert parse_color(color_input) == expected

    @pytest.mark.parametrize("invalid_color", [
        "#GG0000",
        "256,0,0",
        "255,255",
        "invalid",
        "#12345",
        "12345G",
    ])
    def test_invalid_colors_parametrized(self, invalid_color):
        """Test various invalid color formats."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_color(invalid_color)
