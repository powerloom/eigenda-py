"""Tests for blob request signing."""

import pytest
from unittest.mock import Mock, patch
from eth_account import Account
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.core.types import BlobKey


class TestLocalBlobRequestSigner:
    """Test LocalBlobRequestSigner class."""
    
    @pytest.fixture
    def test_private_key(self):
        """Generate a test private key."""
        account = Account.create()
        return account.key.hex()
    
    @pytest.fixture
    def signer(self, test_private_key):
        """Create a test signer."""
        return LocalBlobRequestSigner(test_private_key)
    
    def test_signer_creation(self, test_private_key):
        """Test creating a signer."""
        # With 0x prefix
        signer1 = LocalBlobRequestSigner(test_private_key)
        assert signer1.private_key is not None
        
        # Without 0x prefix
        key_no_prefix = test_private_key[2:] if test_private_key.startswith('0x') else test_private_key
        signer2 = LocalBlobRequestSigner(key_no_prefix)
        assert signer2.private_key is not None
        
        # Should have same account
        assert signer1.get_account_id() == signer2.get_account_id()
    
    def test_get_account_id(self, signer):
        """Test getting account ID."""
        account_id = signer.get_account_id()
        assert isinstance(account_id, str)
        assert account_id.startswith('0x')
        assert len(account_id) == 42  # Ethereum address length
    
    def test_sign_payment_state_request(self, signer):
        """Test signing a payment state request."""
        timestamp = 1234567890000000000  # nanoseconds
        signature = signer.sign_payment_state_request(timestamp)
        
        assert isinstance(signature, bytes)
        assert len(signature) == 65  # r(32) + s(32) + v(1)
        
        # Test v value adjustment (should be 0 or 1)
        v = signature[64]
        assert v in [0, 1]
    
    def test_sign_blob_request_with_blob_header(self, signer):
        """Test signing a blob request with our BlobHeader type."""
        # Create a mock BlobHeader with blob_key method
        header = Mock()
        mock_blob_key = Mock()
        mock_blob_key._bytes = b'x' * 32  # 32 byte key
        header.blob_key.return_value = mock_blob_key
        
        signature = signer.sign_blob_request(header)
        
        assert isinstance(signature, bytes)
        assert len(signature) == 65  # r(32) + s(32) + v(1)
        
        # Test v value adjustment
        v = signature[64]
        assert v in [0, 1]
    
    def test_sign_blob_request_with_proto_header(self, signer):
        """Test signing a blob request with protobuf header."""
        # Create a mock protobuf header (no blob_key attribute)
        proto_header = Mock()
        del proto_header.blob_key  # Ensure it doesn't have blob_key attribute
        
        # Mock the calculate_blob_key function
        with patch('eigenda.auth.signer.calculate_blob_key') as mock_calc:
            mock_calc.return_value = b'y' * 32  # 32 byte key
            
            signature = signer.sign_blob_request(proto_header)
            
            assert isinstance(signature, bytes)
            assert len(signature) == 65
            mock_calc.assert_called_once_with(proto_header)
    
    def test_sign_blob_request_v_value_edge_cases(self, signer):
        """Test v value adjustment edge cases."""
        header = Mock()
        mock_blob_key = Mock()
        mock_blob_key._bytes = b'z' * 32
        header.blob_key.return_value = mock_blob_key
        
        # Mock the account's unsafe_sign_hash to control v value
        original_sign = signer.account.unsafe_sign_hash
        
        # Test with v=27 (should be adjusted to 0)
        mock_signature = Mock()
        mock_signature.signature = b'r' * 32 + b's' * 32 + bytes([27])
        signer.account.unsafe_sign_hash = Mock(return_value=mock_signature)
        
        signature = signer.sign_blob_request(header)
        assert signature[64] == 0
        
        # Test with v=28 (should be adjusted to 1)
        mock_signature.signature = b'r' * 32 + b's' * 32 + bytes([28])
        signature = signer.sign_blob_request(header)
        assert signature[64] == 1
        
        # Test with v=0 (should remain 0)
        mock_signature.signature = b'r' * 32 + b's' * 32 + bytes([0])
        signature = signer.sign_blob_request(header)
        assert signature[64] == 0
        
        # Test with v=1 (should remain 1)
        mock_signature.signature = b'r' * 32 + b's' * 32 + bytes([1])
        signature = signer.sign_blob_request(header)
        assert signature[64] == 1
        
        # Restore original
        signer.account.unsafe_sign_hash = original_sign
    
    def test_hash_payment_state_request(self, signer):
        """Test the private _hash_payment_state_request method."""
        account_id = "0x1234567890123456789012345678901234567890"
        timestamp = 1234567890000000000
        
        hash_result = signer._hash_payment_state_request(account_id, timestamp)
        
        assert isinstance(hash_result, bytes)
        assert len(hash_result) == 32  # SHA256 hash
    
    def test_sign_payment_state_request_v_adjustment(self, signer):
        """Test v value adjustment in payment state signing."""
        timestamp = 9876543210000000000
        
        # Mock the account's unsafe_sign_hash
        original_sign = signer.account.unsafe_sign_hash
        
        # Test with v=27
        mock_signature = Mock()
        mock_signature.signature = b'a' * 32 + b'b' * 32 + bytes([27])
        signer.account.unsafe_sign_hash = Mock(return_value=mock_signature)
        
        signature = signer.sign_payment_state_request(timestamp)
        assert signature[64] == 0
        
        # Test with v=28
        mock_signature.signature = b'a' * 32 + b'b' * 32 + bytes([28])
        signature = signer.sign_payment_state_request(timestamp)
        assert signature[64] == 1
        
        # Restore
        signer.account.unsafe_sign_hash = original_sign