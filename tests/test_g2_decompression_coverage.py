"""Specific tests to cover lines 72 and 77 in g2_decompression.py"""

from unittest.mock import patch
from eigenda.utils.g2_decompression import (
    decompress_g2_point_full,
    COMPRESSED_LARGEST,
    COMPRESSED_SMALLEST,
    P
)
from eigenda.utils.fp2_arithmetic import Fp2


class TestG2DecompressionCoverage:
    """Tests specifically designed to cover lines 72 and 77."""

    def test_line_72_y_a1_zero_y_a0_large(self):
        """Test to cover line 72: y.a1 == 0 and y.a0 > P // 2"""
        # We need to mock sqrt_fp2 to return a specific y value

        # Create a compressed point
        compressed = bytearray(64)
        compressed[0] = COMPRESSED_SMALLEST
        compressed[31] = 1  # x1 = 1
        compressed[63] = 1  # x0 = 1

        # Mock sqrt_fp2 to return y with a1=0 and a0 > P//2
        mock_y = Fp2(P // 2 + 1, 0)  # y.a1 = 0, y.a0 > P//2

        with patch('eigenda.utils.g2_decompression.sqrt_fp2') as mock_sqrt:
            mock_sqrt.return_value = (mock_y, True)

            # This should trigger line 72
            (x, y) = decompress_g2_point_full(bytes(compressed))

            # Verify the result
            assert x == (1, 1)
            # With COMPRESSED_SMALLEST and y_is_larger=True, y should be negated
            assert y == ((-mock_y.a0) % P, 0)

    def test_line_77_compressed_largest_y_not_larger(self):
        """Test to cover line 77: COMPRESSED_LARGEST with y_is_larger = False"""
        # Create a compressed point with COMPRESSED_LARGEST flag
        compressed = bytearray(64)
        compressed[0] = COMPRESSED_LARGEST
        compressed[31] = 2  # x1 = 2
        compressed[63] = 2  # x0 = 2

        # Mock sqrt_fp2 to return y with both components <= P//2
        # This ensures y_is_larger = False
        mock_y = Fp2(100, 100)  # Both components well below P//2

        with patch('eigenda.utils.g2_decompression.sqrt_fp2') as mock_sqrt:
            mock_sqrt.return_value = (mock_y, True)

            # This should trigger line 77
            (x, y) = decompress_g2_point_full(bytes(compressed))

            # Verify the result
            assert x == (2, 2)
            # With COMPRESSED_LARGEST and y_is_larger=False, y should be negated
            assert y == ((-mock_y.a0) % P, (-mock_y.a1) % P)

    def test_both_conditions_different_points(self):
        """Test both conditions with different valid points."""
        # Test 1: Point that triggers line 72
        compressed1 = bytearray(64)
        compressed1[0] = COMPRESSED_SMALLEST
        compressed1[31] = 3
        compressed1[63] = 3

        # y with a1=0, a0 > P//2
        mock_y1 = Fp2(P - 1000, 0)  # a0 is large (> P//2), a1 = 0

        with patch('eigenda.utils.g2_decompression.sqrt_fp2') as mock_sqrt:
            mock_sqrt.return_value = (mock_y1, True)
            (x1, y1) = decompress_g2_point_full(bytes(compressed1))
            # y_is_larger = True, COMPRESSED_SMALLEST -> negate y
            assert y1 == ((-mock_y1.a0) % P, 0)

        # Test 2: Point that triggers line 77
        compressed2 = bytearray(64)
        compressed2[0] = COMPRESSED_LARGEST
        compressed2[31] = 4
        compressed2[63] = 4

        # y with both components small (< P//2)
        mock_y2 = Fp2(1000, 2000)  # Both well below P//2

        with patch('eigenda.utils.g2_decompression.sqrt_fp2') as mock_sqrt:
            mock_sqrt.return_value = (mock_y2, True)
            (x2, y2) = decompress_g2_point_full(bytes(compressed2))
            # y_is_larger = False, COMPRESSED_LARGEST -> negate y
            assert y2 == ((-mock_y2.a0) % P, (-mock_y2.a1) % P)
