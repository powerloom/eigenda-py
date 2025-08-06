"""Tests for blob encoding/decoding."""

from eigenda.codec import decode_blob_data, encode_blob_data


class TestBlobCodec:
    """Test blob encoding and decoding functions."""

    def test_encode_empty_data(self):
        """Test encoding empty data."""
        result = encode_blob_data(b"")
        assert result == b""

    def test_encode_single_byte(self):
        """Test encoding a single byte."""
        data = b"A"
        encoded = encode_blob_data(data)
        assert len(encoded) == 32  # Padded to 32 bytes
        assert encoded[0] == 0x00
        assert encoded[1] == ord("A")
        assert encoded[2:] == b"\x00" * 30  # Rest is padding

    def test_encode_31_bytes(self):
        """Test encoding exactly 31 bytes (one chunk)."""
        data = b"A" * 31
        encoded = encode_blob_data(data)
        assert len(encoded) == 32
        assert encoded[0] == 0x00
        assert encoded[1:32] == data

    def test_encode_32_bytes(self):
        """Test encoding 32 bytes (needs two chunks)."""
        data = b"A" * 32
        encoded = encode_blob_data(data)
        assert len(encoded) == 64  # Two 32-byte chunks
        assert encoded[0] == 0x00
        assert encoded[1:32] == data[:31]
        assert encoded[32] == 0x00
        assert encoded[33] == ord("A")  # Last byte of original data
        assert encoded[34:] == b"\x00" * 30  # Rest is padding

    def test_encode_decode_roundtrip(self):
        """Test that encode followed by decode returns original data."""
        # Note: decode strips trailing null bytes, so data ending with nulls
        # won't roundtrip perfectly. This is a known limitation.
        # In practice, the blob length is tracked separately in the protocol.
        test_cases = [
            b"",  # Empty data
            b"A" * 31,  # Exactly one chunk
            b"A" * 62,  # Exactly two chunks
            b"Hello",  # Small data
            b"Test\x00\x00",  # Data with trailing nulls
        ]

        for original in test_cases:
            encoded = encode_blob_data(original)
            # Use original_length parameter to get exact roundtrip
            decoded = decode_blob_data(encoded, len(original))
            assert decoded == original, f"Roundtrip failed for data of length {len(original)}"

    def test_decode_empty_data(self):
        """Test decoding empty data."""
        result = decode_blob_data(b"")
        assert result == b""

    def test_decode_with_padding(self):
        """Test decoding data that includes padding."""
        # Test that decoder correctly handles padding
        encoded = b"\x00Hello" + b"\x00" * 26  # 32 byte chunk with padding
        decoded = decode_blob_data(encoded, 5)  # Specify original length
        assert decoded == b"Hello"  # Correct length preserved

    def test_decode_strips_leading_byte(self):
        """Test that decode strips the leading padding byte from each chunk."""
        # First chunk: 0x00 + 31 bytes of 'A'
        # Second chunk: 0x00 + 1 byte 'B' + 30 bytes padding
        encoded = b"\x00" + b"A" * 31 + b"\x00B" + b"\x00" * 30
        decoded = decode_blob_data(encoded)
        assert decoded[:32] == b"A" * 31 + b"B"
