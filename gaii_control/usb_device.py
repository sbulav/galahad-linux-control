"""USB communication for Lian Li Galahad II LCD control."""

from typing import Tuple, Any
import usb.core
import usb.util
import time

from .config import (
    VENDOR_ID,
    PRODUCT_ID,
    INTERFACE_CONTROL,
    USBProtocol,
    RGBPacket,
    VideoPacket,
)


def send_h264_frame(endpoint: usb.core.Endpoint, h264_data: bytes) -> None:
    """Send H.264 frame data to USB device in chunked packets.
    
    The device expects packets with a specific structure:
    - Header bytes (0x02, 0x0D)
    - Total frame size (4 bytes, big-endian)
    - Sequence number (3 bytes, big-endian)
    - Chunk size (2 bytes, big-endian)
    - Payload (up to 1013 bytes)
    - Padding to 1024 bytes total
    
    Args:
        endpoint: USB endpoint to write to
        h264_data: bytes of H.264 encoded video data
    """
    offset = 0
    seq = 0

    while offset < len(h264_data):
        chunk_len = min(USBProtocol.CHUNK_SIZE, len(h264_data) - offset)
        chunk = h264_data[offset : offset + chunk_len]

        packet = bytearray(USBProtocol.MAX_PACKET_SIZE)
        packet[VideoPacket.HEADER_1] = USBProtocol.HEADER_BYTE_1
        packet[VideoPacket.HEADER_2] = USBProtocol.HEADER_BYTE_2
        packet[VideoPacket.DATA_LEN_B3] = (len(h264_data) >> 24) & 0xFF
        packet[VideoPacket.DATA_LEN_B2] = (len(h264_data) >> 16) & 0xFF
        packet[VideoPacket.DATA_LEN_B1] = (len(h264_data) >> 8) & 0xFF
        packet[VideoPacket.DATA_LEN_B0] = len(h264_data) & 0xFF
        packet[VideoPacket.SEQ_B2] = (seq >> 16) & 0xFF
        packet[VideoPacket.SEQ_B1] = (seq >> 8) & 0xFF
        packet[VideoPacket.SEQ_B0] = seq & 0xFF
        packet[VideoPacket.CHUNK_LEN_B1] = (chunk_len >> 8) & 0xFF
        packet[VideoPacket.CHUNK_LEN_B0] = chunk_len & 0xFF
        packet[VideoPacket.PAYLOAD : VideoPacket.PAYLOAD + chunk_len] = chunk

        endpoint.write(bytes(packet), timeout=USBProtocol.TIMEOUT_MS)

        offset += chunk_len
        seq += 1
        time.sleep(USBProtocol.SLEEP_BETWEEN_PACKETS_S)


def find_device() -> Any:
    """Find and return the Lian Li Galahad II LCD device.
    
    Returns:
        USB device object or None if not found
    """
    return usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)


def setup_device(device: Any) -> None:
    """Configure USB device for communication.
    
    Args:
        device: USB device object
        
    Raises:
        USBError: If device configuration fails
    """
    # Detach kernel driver if active on any interface
    for i in [0, 1, 2]:
        try:
            if device.is_kernel_driver_active(i):
                device.detach_kernel_driver(i)
        except:
            pass

    device.set_configuration()
    usb.util.claim_interface(device, INTERFACE_CONTROL)


def get_endpoint(device: Any) -> Any:
    """Get the output endpoint for video frames.
    
    Args:
        device: USB device object
        
    Returns:
        USB endpoint object for writing
    """
    cfg = device.get_active_configuration()
    intf = cfg[(INTERFACE_CONTROL, 0)]
    endpoint = usb.util.find_descriptor(
        intf,
        custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
        == usb.util.ENDPOINT_OUT,
    )
    return endpoint


def set_rgb_color(endpoint: Any, rgb_color: Tuple[int, int, int]) -> None:
    """Set RGB pump color via USB.
    
    Packet structure for RGB pump control:
    - Bytes 0-1: Header (0x01, 0x83)
    - Bytes 2-4: Reserved
    - Byte 5: Payload size (19)
    - Bytes 6-9: Payload header (0x00, 0x03, 0x04, 0x00)
    - Bytes 10-12: RGB color (R, G, B)
    - Bytes 13-63: Padding/reserved
    
    Args:
        endpoint: USB endpoint to write to
        rgb_color: tuple of (R, G, B) values 0-255
    """
    packet = bytearray(RGBPacket.SIZE)
    packet[0] = RGBPacket.HEADER_BYTE  # 0x01
    packet[1] = RGBPacket.COLOR_CMD    # 0x83
    packet[RGBPacket.COLOR_OFFSET] = RGBPacket.PAYLOAD_SIZE  # packet[5] = 19
    
    # Set the RGB payload header (required by device protocol)
    # This header must be present before RGB values
    packet[6] = 0x00
    packet[7] = 0x03
    packet[8] = 0x04
    packet[9] = 0x00
    
    # Set RGB values after the header
    packet[10] = rgb_color[0]  # Red
    packet[11] = rgb_color[1]  # Green
    packet[12] = rgb_color[2]  # Blue
    
    # Rest of payload is zeros (already initialized)
    endpoint.write(bytes(packet), timeout=1000)


def cleanup_device(device: Any | None) -> None:
    """Safely release USB device resources and restore kernel driver.
    
    Ensures the device is left in a clean state for subsequent use or other
    applications. This function is idempotent - it's safe to call multiple times.
    
    Args:
        device: USB device object or None
    """
    if device is None:
        return
    
    try:
        usb.util.release_interface(device, INTERFACE_CONTROL)
    except Exception as e:
        print(f"  ⚠️  Warning: Failed to release interface: {e}")
    
    try:
        device.attach_kernel_driver(INTERFACE_CONTROL)
    except Exception as e:
        print(f"  ⚠️  Warning: Failed to re-attach kernel driver: {e}")
    
    try:
        device.reset()
    except Exception as e:
        print(f"  ⚠️  Warning: Failed to reset device: {e}")
