"""Additional tests for client_v2_full.py - only working tests."""

from unittest.mock import Mock, patch

import grpc
import pytest

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full, PaymentType
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
            payment_config=PaymentConfig(price_per_symbol=447, min_num_symbols=4096),
        )

    def test_disperse_blob_non_grpc_error(self, client):
        """Test disperse_blob with non-gRPC exception."""
        client._payment_type = PaymentType.ON_DEMAND
        client._has_reservation = False

        with patch.object(client, "_connect"):
            with patch.object(client, "_stub") as mock_stub:
                # Mock GetBlobCommitment to raise ValueError
                mock_stub.GetBlobCommitment.side_effect = ValueError("Invalid data")
                
                with pytest.raises(ValueError) as exc_info:
                    client.disperse_blob(b"test data")

                assert str(exc_info.value) == "Invalid data"

    def test_disperse_blob_other_grpc_error(self, client):
        """Test disperse_blob with gRPC error."""
        client._payment_type = PaymentType.RESERVATION
        client._has_reservation = True
        client._payment_state = Mock()
        # Ensure accountant exists with proper state
        from eigenda.payment import SimpleAccountant
        client.accountant = SimpleAccountant(client.signer.get_account_id())
        client.accountant.cumulative_payment = 0

        with patch.object(client, "_connect"):
            with patch.object(client, "_stub") as mock_stub:
                # Mock GetBlobCommitment
                mock_commitment_reply = Mock()
                mock_commitment_reply.blob_commitment = Mock()
                mock_stub.GetBlobCommitment.return_value = mock_commitment_reply
                
                # Mock the protobuf message creation to avoid issues
                mock_blob_header = Mock()
                mock_request = Mock()
                with patch("eigenda.client_v2_full.common_v2_pb2.BlobHeader") as mock_header_class:
                    mock_header_class.return_value = mock_blob_header
                    with patch("eigenda.client_v2_full.common_v2_pb2.PaymentHeader"):
                        with patch("eigenda.client_v2_full.disperser_v2_pb2.DisperseBlobRequest") as mock_request_class:
                            mock_request_class.return_value = mock_request
                            # Create a proper gRPC error that inherits from BaseException
                            class MockGrpcError(Exception):
                                def code(self):
                                    return grpc.StatusCode.UNAVAILABLE
                                def details(self):
                                    return "Service unavailable"
                            
                            mock_stub.DisperseBlob.side_effect = MockGrpcError("Service unavailable")
                            
                            with pytest.raises(Exception, match="Service unavailable"):
                                client.disperse_blob(b"test data")
