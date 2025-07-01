"""Complete tests for core/types.py to achieve 100% coverage."""

import pytest
from eigenda.core.types import (
    BlobKey, BlobStatus, G1Commitment, G2Commitment, 
    BlobCommitments, PaymentMetadata, BlobHeader
)


class TestBlobKey:
    """Complete tests for BlobKey class."""
    
    def test_blob_key_creation_valid(self):
        """Test creating BlobKey with valid 32 bytes."""
        data = b'x' * 32
        key = BlobKey(data)
        assert bytes(key) == data
    
    def test_blob_key_creation_invalid_length(self):
        """Test BlobKey creation with invalid length (line 32)."""
        with pytest.raises(ValueError, match="BlobKey must be 32 bytes, got 5"):
            BlobKey(b'short')
    
    def test_blob_key_hex(self):
        """Test hex() method (line 37)."""
        data = b'\xaa' * 32
        key = BlobKey(data)
        assert key.hex() == 'aa' * 32
    
    def test_blob_key_from_hex_with_0x(self):
        """Test from_hex with 0x prefix (lines 43-45)."""
        hex_str = '0x' + 'bb' * 32
        key = BlobKey.from_hex(hex_str)
        assert bytes(key) == b'\xbb' * 32
    
    def test_blob_key_from_hex_with_0X(self):
        """Test from_hex with 0X prefix (line 43)."""
        hex_str = '0X' + 'cc' * 32
        key = BlobKey.from_hex(hex_str)
        assert bytes(key) == b'\xcc' * 32
    
    def test_blob_key_from_hex_without_prefix(self):
        """Test from_hex without prefix (line 45)."""
        hex_str = 'dd' * 32
        key = BlobKey.from_hex(hex_str)
        assert bytes(key) == b'\xdd' * 32
    
    def test_blob_key_from_bytes(self):
        """Test from_bytes classmethod (line 50)."""
        data = b'e' * 32
        key = BlobKey.from_bytes(data)
        assert bytes(key) == data
    
    def test_blob_key_repr(self):
        """Test __repr__ method."""
        data = b'\xff' * 32
        key = BlobKey(data)
        assert repr(key) == f"BlobKey({'ff' * 32})"
    
    def test_blob_key_equality(self):
        """Test __eq__ method (lines 59-61)."""
        key1 = BlobKey(b'a' * 32)
        key2 = BlobKey(b'a' * 32)
        key3 = BlobKey(b'b' * 32)
        
        assert key1 == key2
        assert key1 != key3
        assert key1 != "not a blob key"  # Test line 60


class TestBlobHeader:
    """Complete tests for BlobHeader class."""
    
    def test_blob_header_complete_flow(self):
        """Test blob_key() method and internal methods (lines 115-148)."""
        # Create all required components
        g1_commitment = G1Commitment(x=b'x' * 32, y=b'y' * 32)
        g2_commitment1 = G2Commitment(
            x_a0=b'a' * 32, x_a1=b'b' * 32,
            y_a0=b'c' * 32, y_a1=b'd' * 32
        )
        g2_commitment2 = G2Commitment(
            x_a0=b'e' * 32, x_a1=b'f' * 32,
            y_a0=b'g' * 32, y_a1=b'h' * 32
        )
        
        blob_commitments = BlobCommitments(
            commitment=g1_commitment,
            length_commitment=g2_commitment1,
            length_proof=g2_commitment2,
            length=1000
        )
        
        payment_metadata = PaymentMetadata(
            account_id="0x1234567890123456789012345678901234567890",
            cumulative_payment=12345
        )
        
        blob_header = BlobHeader(
            blob_version=1,
            blob_commitments=blob_commitments,
            quorum_numbers=[0, 1, 2],
            payment_metadata=payment_metadata
        )
        
        # Test blob_key() method - this calls _serialize_commitments and _hash_payment_metadata
        blob_key = blob_header.blob_key()
        assert isinstance(blob_key, BlobKey)
        assert len(bytes(blob_key)) == 32
        
        # Verify it's deterministic
        blob_key2 = blob_header.blob_key()
        assert blob_key == blob_key2
    
    def test_blob_header_different_inputs_produce_different_keys(self):
        """Test that different headers produce different keys (line 127)."""
        # Base components
        g1_commitment = G1Commitment(x=b'x' * 32, y=b'y' * 32)
        g2_commitment = G2Commitment(
            x_a0=b'a' * 32, x_a1=b'b' * 32,
            y_a0=b'c' * 32, y_a1=b'd' * 32
        )
        
        blob_commitments = BlobCommitments(
            commitment=g1_commitment,
            length_commitment=g2_commitment,
            length_proof=g2_commitment,
            length=1000
        )
        
        payment_metadata = PaymentMetadata(
            account_id="0x1234567890123456789012345678901234567890",
            cumulative_payment=12345
        )
        
        # Create two headers with different versions
        header1 = BlobHeader(
            blob_version=1,
            blob_commitments=blob_commitments,
            quorum_numbers=[0, 1],
            payment_metadata=payment_metadata
        )
        
        header2 = BlobHeader(
            blob_version=2,  # Different version
            blob_commitments=blob_commitments,
            quorum_numbers=[0, 1],
            payment_metadata=payment_metadata
        )
        
        key1 = header1.blob_key()
        key2 = header2.blob_key()
        
        assert key1 != key2  # Different headers should produce different keys