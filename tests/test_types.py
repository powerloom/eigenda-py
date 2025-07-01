"""Tests for core types."""

import pytest
from eigenda.core.types import BlobKey, BlobStatus


class TestBlobKey:
    """Test BlobKey class."""

    def test_blob_key_creation(self):
        """Test creating a BlobKey."""
        data = b'\x00' * 32
        key = BlobKey(data)
        assert bytes(key) == data

    def test_blob_key_invalid_length(self):
        """Test that BlobKey rejects invalid lengths."""
        with pytest.raises(ValueError, match="BlobKey must be 32 bytes"):
            BlobKey(b'\x00' * 31)

        with pytest.raises(ValueError, match="BlobKey must be 32 bytes"):
            BlobKey(b'\x00' * 33)

    def test_blob_key_hex(self):
        """Test hex representation."""
        data = b'\x00' * 16 + b'\x0f' * 16
        key = BlobKey(data)
        hex_str = key.hex()
        assert hex_str == '00' * 16 + '0f' * 16

    def test_blob_key_from_hex(self):
        """Test creating BlobKey from hex string."""
        hex_str = '00' * 16 + '0f' * 16
        key = BlobKey.from_hex(hex_str)
        assert bytes(key) == b'\x00' * 16 + b'\x0f' * 16

        # Test with 0x prefix
        key2 = BlobKey.from_hex('0x' + hex_str)
        assert key == key2

        # Test with 0X prefix
        key3 = BlobKey.from_hex('0X' + hex_str)
        assert key == key3

    def test_blob_key_equality(self):
        """Test BlobKey equality."""
        data1 = b'\x00' * 32
        data2 = b'\xff' * 32

        key1a = BlobKey(data1)
        key1b = BlobKey(data1)
        key2 = BlobKey(data2)

        assert key1a == key1b
        assert key1a != key2
        assert key1a != "not a blob key"


class TestBlobStatus:
    """Test BlobStatus enum."""

    def test_blob_status_values(self):
        """Test that all expected status values exist."""
        assert BlobStatus.UNKNOWN.value == 0
        assert BlobStatus.PROCESSING.value == 1
        assert BlobStatus.GATHERING_SIGNATURES.value == 2
        assert BlobStatus.COMPLETE.value == 3
        assert BlobStatus.FAILED.value == 4
        assert BlobStatus.INSUFFICIENT_SIGNATURES.value == 5
