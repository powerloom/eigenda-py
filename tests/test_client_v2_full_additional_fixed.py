"""Additional tests for client_v2_full.py - only working tests."""

import pytest
import grpc
from unittest.mock import Mock, patch
from eigenda.client_v2_full import DisperserClientV2Full, PaymentType
from eigenda.core.types import BlobStatus, BlobKey
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.payment import PaymentConfig


class TestDisperserClientV2FullAdditional:
    """Additional tests for DisperserClientV2Full."""
    
    @pytest.fixture
    def mock_signer(self):
        """Create a mock signer."""
        signer = Mock(spec=LocalBlobRequestSigner)
        signer.get_account_id.return_value = "0x1234567890123456789012345678901234567890"
        return signer
    
    @pytest.fixture
    def client(self, mock_signer):
        """Create a test client."""
        return DisperserClientV2Full(
            hostname="test.disperser.com",
            port=443,
            use_secure_grpc=True,
            signer=mock_signer,
            payment_config=PaymentConfig(price_per_symbol=447, min_num_symbols=4096)
        )
    
    def test_disperse_blob_non_grpc_error(self, client):
        """Test disperse_blob with non-gRPC exception."""
        client._payment_type = PaymentType.ON_DEMAND
        client._has_reservation = False
        
        # Mock parent to raise generic exception
        with patch.object(DisperserClientV2Full.__bases__[0], 'disperse_blob') as mock_parent:
            mock_parent.side_effect = ValueError("Invalid data")
            
            with pytest.raises(ValueError) as exc_info:
                client.disperse_blob(b'test data', 0, [0, 1])
            
            assert str(exc_info.value) == "Invalid data"
    
    def test_disperse_blob_other_grpc_error(self, client):
        """Test disperse_blob with non-INVALID_ARGUMENT gRPC error."""
        client._payment_type = PaymentType.RESERVATION
        client._has_reservation = True
        
        # Mock gRPC error that's not INVALID_ARGUMENT
        error = grpc.RpcError()
        error.code = Mock(return_value=grpc.StatusCode.UNAVAILABLE)
        error.details = Mock(return_value="Service unavailable")
        
        with patch.object(DisperserClientV2Full.__bases__[0], 'disperse_blob') as mock_parent:
            mock_parent.side_effect = error
            
            with pytest.raises(grpc.RpcError):
                client.disperse_blob(b'test data', 0, [0, 1])
            
            # Should not retry for other errors
            assert mock_parent.call_count == 1