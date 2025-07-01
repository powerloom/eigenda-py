"""Tests to achieve 100% coverage for gnark_decompression.py"""

import pytest
from unittest.mock import patch
from eigenda.utils.gnark_decompression import (
    decompress_g1_point_gnark, decompress_g2_point_gnark,
    COMPRESSED_INFINITY, COMPRESSED_SMALLEST, COMPRESSED_LARGEST
)
from eigenda.utils.bn254_field import P


class TestGnarkDecompressionCoverage:
    """Tests for complete coverage of gnark_decompression.py"""

    def test_g1_invalid_length_line_29(self):
        """Test line 29 - invalid compressed data length"""
        with pytest.raises(ValueError, match="Expected 32 bytes for compressed G1 point, got 10"):
            decompress_g1_point_gnark(b"short data")

    def test_g1_point_at_infinity_line_36(self):
        """Test line 36 - point at infinity"""
        # Create a compressed point with infinity flag
        compressed = bytearray(32)
        compressed[0] = COMPRESSED_INFINITY

        x, y = decompress_g1_point_gnark(bytes(compressed))
        assert x == 0
        assert y == 0

    def test_g1_invalid_x_coordinate_line_46(self):
        """Test line 46 - x coordinate with no valid y"""
        # Create a compressed point with an x that has no valid y
        compressed = bytearray(32)
        compressed[0] = COMPRESSED_SMALLEST
        # Set x to a value that's not on the curve
        # P - 1 typically won't have a valid y
        x_bytes = (P - 1).to_bytes(32, 'big')
        compressed[1:] = x_bytes[1:]

        with patch('eigenda.utils.gnark_decompression.compute_y_from_x') as mock_compute:
            mock_compute.return_value = (0, False)  # No valid y exists

            with pytest.raises(ValueError, match="No valid point exists for x="):
                decompress_g1_point_gnark(bytes(compressed))

    def test_g1_compressed_largest_not_larger_lines_53_54(self):
        """Test lines 53-54 - COMPRESSED_LARGEST with y not larger"""
        compressed = bytearray(32)
        compressed[0] = COMPRESSED_LARGEST
        # Set a valid x coordinate
        x = 1
        x_bytes = x.to_bytes(32, 'big')
        compressed[1:] = x_bytes[1:]
        compressed[0] |= COMPRESSED_LARGEST

        with patch('eigenda.utils.gnark_decompression.compute_y_from_x') as mock_compute:
            # Return a y that's less than P//2 (not larger)
            small_y = P // 4
            mock_compute.return_value = (small_y, True)

            x_result, y_result = decompress_g1_point_gnark(bytes(compressed))
            assert x_result == x
            assert y_result == P - small_y  # Should be flipped

    def test_g1_compressed_smallest_larger_lines_57(self):
        """Test line 57 - COMPRESSED_SMALLEST with y larger"""
        compressed = bytearray(32)
        compressed[0] = COMPRESSED_SMALLEST
        # Set a valid x coordinate
        x = 1
        x_bytes = x.to_bytes(32, 'big')
        compressed[1:] = x_bytes[1:]

        with patch('eigenda.utils.gnark_decompression.compute_y_from_x') as mock_compute:
            # Return a y that's greater than P//2 (larger)
            large_y = P // 2 + 100
            mock_compute.return_value = (large_y, True)

            x_result, y_result = decompress_g1_point_gnark(bytes(compressed))
            assert x_result == x
            assert y_result == P - large_y  # Should be flipped

    def test_g1_invalid_compression_flag_lines_58_59(self):
        """Test lines 58-59 - invalid compression flag"""
        compressed = bytearray(32)
        # Set an invalid flag (not one of the defined compression flags)
        compressed[0] = 0x20  # Some invalid flag

        with patch('eigenda.utils.gnark_decompression.compute_y_from_x') as mock_compute:
            mock_compute.return_value = (100, True)

            with pytest.raises(ValueError, match="Invalid compression flag: 0x0"):
                decompress_g1_point_gnark(bytes(compressed))

    def test_g2_successful_decompression_line_81(self):
        """Test line 81 - successful G2 decompression"""
        compressed = b'test' * 16  # 64 bytes

        with patch('eigenda.utils.g2_decompression.decompress_g2_point_full') as mock_decompress:
            # Mock successful decompression
            mock_decompress.return_value = ((1, 2), (3, 4))

            result = decompress_g2_point_gnark(compressed)
            assert result == ([1, 2], [3, 4])
            mock_decompress.assert_called_once_with(compressed)
