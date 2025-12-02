"""Pytest configuration and shared fixtures for galahad-linux-control tests."""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from PIL import Image
import tempfile

# Add parent directory to path so we can import glc_control
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_image():
    """Create a temporary test image."""
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f.name)
        temp_path = f.name
    yield temp_path
    # Cleanup
    try:
        os.unlink(temp_path)
    except:
        pass


@pytest.fixture
def temp_large_image():
    """Create a larger temporary test image."""
    img = Image.new("RGB", (1000, 800), color=(0, 255, 0))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f.name)
        temp_path = f.name
    yield temp_path
    try:
        os.unlink(temp_path)
    except:
        pass


@pytest.fixture
def temp_small_image():
    """Create a small temporary test image."""
    img = Image.new("RGB", (100, 50), color=(0, 0, 255))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f.name)
        temp_path = f.name
    yield temp_path
    try:
        os.unlink(temp_path)
    except:
        pass


@pytest.fixture
def mock_usb_endpoint():
    """Create a mock USB endpoint."""
    endpoint = Mock()
    endpoint.write = Mock(return_value=1024)
    return endpoint


@pytest.fixture
def mock_device():
    """Create a mock USB device."""
    device = Mock()
    device.is_kernel_driver_active = Mock(return_value=False)
    device.detach_kernel_driver = Mock()
    device.set_configuration = Mock()
    device.get_active_configuration = Mock()
    return device


@pytest.fixture
def sample_h264_data():
    """Create sample H.264 data for testing."""
    # Minimal H.264 frame (NAL unit header + some data)
    return b"\x00\x00\x00\x01\x67\x42\x00\x0a\xff\xe1\x00\x16\x00" + b"\x00" * 100


@pytest.fixture(autouse=True)
def mock_psutil():
    """Mock psutil to avoid hardware dependency."""
    with patch("glc_control.image_processor.psutil.sensors_temperatures") as mock_temps, \
         patch("glc_control.image_processor.psutil.cpu_percent") as mock_cpu:
        mock_temps.return_value = {
            "coretemp": [Mock(current=45.0)],
        }
        mock_cpu.return_value = 50.0
        yield {"temps": mock_temps, "cpu": mock_cpu}


@pytest.fixture(autouse=True)
def mock_subprocess():
    """Mock subprocess for ffmpeg calls."""
    with patch("glc_control.image_processor.subprocess.run") as mock_run:
        # Create a fake H.264 output file for testing
        def run_side_effect(cmd, **kwargs):
            if "ffmpeg" in cmd:
                # Write dummy H.264 data to output file
                output_file = cmd[-1]
                with open(output_file, "wb") as f:
                    f.write(b"\x00\x00\x00\x01\x67" + b"\x00" * 50)
            result = Mock()
            result.returncode = 0
            return result

        mock_run.side_effect = run_side_effect
        yield mock_run


@pytest.fixture(autouse=True)
def mock_fontconfig():
    """Mock fontconfig and os.path.exists to avoid font dependency."""
    with patch("glc_control.image_processor.subprocess.run") as mock_run, \
         patch("glc_control.image_processor.os.path.exists") as mock_exists:
        
        def run_side_effect(cmd, **kwargs):
            if "fc-match" in cmd:
                result = Mock()
                result.returncode = 0
                result.stdout = "/usr/share/fonts/noto/NotoSansMono-Bold.ttf"
                return result
            # Fallback for other subprocess calls
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            return result

        def exists_side_effect(path):
            if isinstance(path, str) and ("font" in path.lower() or "noto" in path.lower()):
                return True
            return False

        mock_run.side_effect = run_side_effect
        mock_exists.side_effect = exists_side_effect
        yield mock_run
