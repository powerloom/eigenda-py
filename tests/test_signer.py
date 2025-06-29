"""Tests for blob request signing."""

import pytest
from eth_account import Account
from eigenda.auth.signer import LocalBlobRequestSigner


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