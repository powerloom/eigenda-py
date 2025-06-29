"""Tests for blob encoding/decoding."""

import pytest
from eigenda.codec import encode_blob_data, decode_blob_data


class TestBlobCodec:
    """Test blob encoding and decoding functions."""
    
    def test_encode_empty_data(self):
        """Test encoding empty data."""
        result = encode_blob_data(b'')
        assert result == b''
    
    def test_encode_single_byte(self):
        """Test encoding a single byte."""
        data = b'A'
        encoded = encode_blob_data(data)
        assert len(encoded) == 2  # 0x00 + 'A'
        assert encoded[0] == 0x00
        assert encoded[1] == ord('A')
    
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
        assert len(encoded) == 33  # 32 + 1 (0x00 + 1 byte in second chunk)
        assert encoded[0] == 0x00
        assert encoded[1:32] == data[:31]
        assert encoded[32] == 0x00
        assert encoded[33:34] == data[31:32]
    
    def test_encode_decode_roundtrip(self):
        """Test that encode followed by decode returns original data."""
        test_cases = [
            b'',
            b'A',
            b'Hello, World!',
            b'A' * 31,
            b'A' * 32,
            b'A' * 100,
            b'\\x00' * 50,
            b'\\xff' * 50,
        ]
        
        for original in test_cases:
            encoded = encode_blob_data(original)
            decoded = decode_blob_data(encoded)
            assert decoded == original, f"Roundtrip failed for data of length {len(original)}"
    
    def test_decode_empty_data(self):
        """Test decoding empty data."""
        result = decode_blob_data(b'')
        assert result == b''
    
    def test_decode_invalid_padding(self):
        """Test decoding handles data with incorrect padding gracefully."""
        # Even if first byte isn't 0x00, decode should still work
        encoded = b'\\x01Hello'
        decoded = decode_blob_data(encoded)
        assert decoded == b'Hello'