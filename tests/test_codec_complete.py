"""Complete tests for blob_codec.py to achieve 100% coverage."""

from eigenda.codec.blob_codec import (
    encode_blob_data, decode_blob_data, validate_field_element, BN254_MODULUS
)


class TestBlobCodecComplete:
    """Complete tests for blob codec functions."""

    def test_encode_empty_data(self):
        """Test encoding empty data (line 27-28)."""
        result = encode_blob_data(b'')
        assert result == b''

    def test_encode_single_byte(self):
        """Test encoding a single byte."""
        data = b'A'
        encoded = encode_blob_data(data)
        assert len(encoded) == 32  # Padded to 32 bytes
        assert encoded[0] == 0x00
        assert encoded[1] == ord('A')
        assert encoded[2:] == b'\x00' * 30  # Rest is padding

    def test_encode_31_bytes(self):
        """Test encoding exactly 31 bytes (one chunk)."""
        data = b'A' * 31
        encoded = encode_blob_data(data)
        assert len(encoded) == 32
        assert encoded[0] == 0x00
        assert encoded[1:32] == data

    def test_encode_32_bytes(self):
        """Test encoding 32 bytes (needs two chunks)."""
        data = b'A' * 32
        encoded = encode_blob_data(data)
        assert len(encoded) == 64  # Two 32-byte chunks
        assert encoded[0] == 0x00
        assert encoded[1:32] == data[:31]
        assert encoded[32] == 0x00
        assert encoded[33] == ord('A')  # Last byte of original data
        assert encoded[34:] == b'\x00' * 30  # Rest is padding

    def test_encode_multiple_chunks(self):
        """Test encoding data spanning multiple chunks."""
        data = b'X' * 100  # Will need 4 chunks (100/31 = 3.2)
        encoded = encode_blob_data(data)
        assert len(encoded) == 128  # 4 chunks * 32 bytes

        # Verify each chunk has proper format
        for i in range(4):
            assert encoded[i * 32] == 0x00  # Leading zero byte

    def test_decode_empty_data(self):
        """Test decoding empty data (line 68-69)."""
        result = decode_blob_data(b'')
        assert result == b''

    def test_decode_single_chunk(self):
        """Test decoding a single 32-byte chunk."""
        encoded = b'\x00' + b'Hello' + b'\x00' * 26
        decoded = decode_blob_data(encoded)
        assert decoded[:5] == b'Hello'

    def test_decode_with_original_length(self):
        """Test decoding with original length specified (lines 81-82)."""
        encoded = b'\x00' + b'Test' + b'\x00' * 27
        decoded = decode_blob_data(encoded, original_length=4)
        assert decoded == b'Test'

    def test_decode_incomplete_chunk(self):
        """Test decoding when last chunk is incomplete (line 76)."""
        # Only 10 bytes instead of full 32
        encoded = b'\x00' + b'ABC' + b'\x00' * 6
        decoded = decode_blob_data(encoded)
        # Should still process what's available
        assert decoded[:3] == b'ABC'

    def test_decode_multiple_chunks_with_length(self):
        """Test decoding multiple chunks with original length."""
        # Two chunks
        encoded = b'\x00' + b'A' * 31 + b'\x00' + b'B' * 5 + b'\x00' * 26
        decoded = decode_blob_data(encoded, original_length=36)
        assert decoded == b'A' * 31 + b'B' * 5

    def test_decode_without_original_length(self):
        """Test decoding without original length (lines 84-87)."""
        encoded = b'\x00' + b'Data' + b'\x00' * 27 + b'\x00' + b'More' + b'\x00' * 27
        decoded = decode_blob_data(encoded)
        # Should include all decoded data including trailing zeros
        assert decoded[:8] == b'Data' + b'\x00' * 4

    def test_validate_field_element_valid(self):
        """Test validate_field_element with valid data (lines 100-107)."""
        # Create a valid 32-byte field element
        valid_data = b'\x00' * 32  # All zeros is valid
        assert validate_field_element(valid_data) is True

        # Test with maximum valid value (just below modulus)
        max_valid = (BN254_MODULUS - 1).to_bytes(32, byteorder='big')
        assert validate_field_element(max_valid) is True

    def test_validate_field_element_invalid_length(self):
        """Test validate_field_element with wrong length (lines 100-101)."""
        # Too short
        assert validate_field_element(b'\x00' * 31) is False
        # Too long
        assert validate_field_element(b'\x00' * 33) is False
        # Empty
        assert validate_field_element(b'') is False

    def test_validate_field_element_invalid_value(self):
        """Test validate_field_element with value >= modulus (line 107)."""
        # Create value equal to modulus
        invalid_data = BN254_MODULUS.to_bytes(32, byteorder='big')
        assert validate_field_element(invalid_data) is False

        # Create value greater than modulus
        invalid_data2 = (BN254_MODULUS + 1).to_bytes(33, byteorder='big')[-32:]
        assert validate_field_element(invalid_data2) is False

    def test_encode_decode_roundtrip(self):
        """Test complete encode/decode roundtrip."""
        test_cases = [
            b'',  # Empty
            b'A',  # Single byte
            b'Hello, World!',  # Small text
            b'X' * 31,  # Exactly one chunk
            b'Y' * 62,  # Exactly two chunks
            b'Z' * 100,  # Multiple chunks
            b'\x00\x01\x02\x03',  # Binary data
        ]

        for original in test_cases:
            encoded = encode_blob_data(original)
            decoded = decode_blob_data(encoded, len(original))
            assert decoded == original, f"Roundtrip failed for {original!r}"
