"""Tests for send_h264_frame() function."""

import pytest
import sys
import os
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glc_control import send_h264_frame


class TestSendH264Frame:
    """Test H.264 frame transmission via USB."""

    def test_send_h264_frame_calls_endpoint(self, mock_usb_endpoint, sample_h264_data):
        """Test that send_h264_frame calls endpoint.write."""
        send_h264_frame(mock_usb_endpoint, sample_h264_data)
        # Endpoint write should be called at least once
        assert mock_usb_endpoint.write.called

    def test_send_h264_frame_small_data(self, mock_usb_endpoint):
        """Test sending small H.264 data that fits in one packet."""
        small_data = b"\x00" * 100
        send_h264_frame(mock_usb_endpoint, small_data)
        assert mock_usb_endpoint.write.called

    def test_send_h264_frame_multiple_packets(self, mock_usb_endpoint):
        """Test sending large H.264 data that requires multiple packets."""
        large_data = b"\x00" * 5000
        send_h264_frame(mock_usb_endpoint, large_data)
        # With 5000 bytes and 1013 chunk size, should need multiple calls
        assert mock_usb_endpoint.write.call_count > 1

    def test_send_h264_frame_exact_chunk_size(self, mock_usb_endpoint):
        """Test sending data that's exactly one chunk size."""
        # 1013 is the default chunk size
        data = b"\x00" * 1013
        send_h264_frame(mock_usb_endpoint, data)
        assert mock_usb_endpoint.write.called

    def test_send_h264_frame_packet_structure(self, mock_usb_endpoint, sample_h264_data):
        """Test that packets have correct structure."""
        send_h264_frame(mock_usb_endpoint, sample_h264_data)
        
        # Get the first packet that was sent
        assert mock_usb_endpoint.write.called
        call_args = mock_usb_endpoint.write.call_args
        packet = call_args[0][0]  # First positional argument
        
        # Packet should be bytes and at least 1024 bytes (with padding)
        assert isinstance(packet, bytes)
        assert len(packet) >= 1024

    def test_send_h264_frame_packet_header(self, mock_usb_endpoint, sample_h264_data):
        """Test that packet headers are set correctly."""
        send_h264_frame(mock_usb_endpoint, sample_h264_data)
        
        call_args = mock_usb_endpoint.write.call_args
        packet = bytearray(call_args[0][0])
        
        # Check packet header bytes
        assert packet[0] == 0x02, "First byte should be 0x02"
        assert packet[1] == 0x0D, "Second byte should be 0x0D"

    def test_send_h264_frame_data_length_encoded(self, mock_usb_endpoint, sample_h264_data):
        """Test that total data length is encoded in packet."""
        send_h264_frame(mock_usb_endpoint, sample_h264_data)
        
        call_args = mock_usb_endpoint.write.call_args
        packet = bytearray(call_args[0][0])
        
        # Bytes 2-5 encode the total length
        encoded_length = (packet[2] << 24) | (packet[3] << 16) | (packet[4] << 8) | packet[5]
        assert encoded_length == len(sample_h264_data)

    def test_send_h264_frame_sequence_number(self, mock_usb_endpoint):
        """Test that sequence numbers increment correctly."""
        data = b"\x00" * 3000  # Large enough for multiple packets
        send_h264_frame(mock_usb_endpoint, data)
        
        # Extract sequence numbers from packets
        sequences = []
        for call in mock_usb_endpoint.write.call_args_list:
            packet = bytearray(call[0][0])
            seq = (packet[6] << 16) | (packet[7] << 8) | packet[8]
            sequences.append(seq)
        
        # Sequences should increment
        for i in range(len(sequences) - 1):
            assert sequences[i + 1] == sequences[i] + 1

    def test_send_h264_frame_chunk_length_encoding(self, mock_usb_endpoint):
        """Test that chunk lengths are encoded correctly."""
        data = b"\xFF" * 2000  # Large data for multiple chunks
        send_h264_frame(mock_usb_endpoint, data)
        
        for call in mock_usb_endpoint.write.call_args_list:
            packet = bytearray(call[0][0])
            chunk_len = (packet[9] << 8) | packet[10]
            # Chunk length should be > 0 and <= 1013
            assert 0 < chunk_len <= 1013

    def test_send_h264_frame_writes_payload(self, mock_usb_endpoint, sample_h264_data):
        """Test that payload is written into packet."""
        send_h264_frame(mock_usb_endpoint, sample_h264_data)
        
        call_args = mock_usb_endpoint.write.call_args
        packet = bytearray(call_args[0][0])
        
        # Packet payload should contain some of the data
        payload = packet[11:]
        assert any(b != 0 for b in payload), "Payload should contain non-zero data"

    def test_send_h264_frame_timeout_parameter(self, mock_usb_endpoint, sample_h264_data):
        """Test that timeout is passed to endpoint.write."""
        send_h264_frame(mock_usb_endpoint, sample_h264_data)
        
        # Get call arguments
        assert mock_usb_endpoint.write.called
        for call in mock_usb_endpoint.write.call_args_list:
            # Check that timeout=2000 is passed as keyword argument
            assert call[1]["timeout"] == 2000

    def test_send_h264_frame_empty_data(self, mock_usb_endpoint):
        """Test handling of empty data."""
        empty_data = b""
        send_h264_frame(mock_usb_endpoint, empty_data)
        # Should not crash, though may not write anything
        # This tests that the function handles edge cases gracefully

    def test_send_h264_frame_single_byte(self, mock_usb_endpoint):
        """Test sending single byte of data."""
        data = b"\xFF"
        send_h264_frame(mock_usb_endpoint, data)
        assert mock_usb_endpoint.write.called

    def test_send_h264_frame_large_data(self, mock_usb_endpoint):
        """Test sending large H.264 data."""
        large_data = b"\x00" * 10000
        send_h264_frame(mock_usb_endpoint, large_data)
        # Should make multiple write calls
        assert mock_usb_endpoint.write.call_count > 5

    def test_send_h264_frame_packet_count(self, mock_usb_endpoint):
        """Test that correct number of packets are sent."""
        # 5000 bytes with 1013 byte chunks = 5 packets
        data = b"\x00" * 5000
        send_h264_frame(mock_usb_endpoint, data)
        
        expected_packets = (5000 + 1012) // 1013  # Ceiling division
        assert mock_usb_endpoint.write.call_count == expected_packets

    def test_send_h264_frame_all_data_transmitted(self, mock_usb_endpoint):
        """Test that all data is transmitted in packets."""
        data = b"A" * 2500
        send_h264_frame(mock_usb_endpoint, data)
        
        total_payload = b""
        for call in mock_usb_endpoint.write.call_args_list:
            packet = bytearray(call[0][0])
            chunk_len = (packet[9] << 8) | packet[10]
            payload = bytes(packet[11:11 + chunk_len])
            total_payload += payload
        
        # All data should be transmitted
        assert data in total_payload or total_payload.startswith(data)

    @pytest.mark.parametrize("data_size", [1, 100, 1013, 2000, 5000, 10000])
    def test_send_h264_frame_various_sizes(self, mock_usb_endpoint, data_size):
        """Test sending data of various sizes."""
        data = b"\x00" * data_size
        send_h264_frame(mock_usb_endpoint, data)
        assert mock_usb_endpoint.write.called
        assert mock_usb_endpoint.write.call_count > 0

    def test_send_h264_frame_minimum_packet_structure(self, mock_usb_endpoint):
        """Test that minimum packet structure is maintained."""
        data = b"\x00" * 100
        send_h264_frame(mock_usb_endpoint, data)
        
        call_args = mock_usb_endpoint.write.call_args
        packet = call_args[0][0]
        
        # Packet must be at least 11 bytes (header + at least some payload)
        assert len(packet) >= 1024
