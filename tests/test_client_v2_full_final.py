"""Final tests for client_v2_full.py to achieve 100% coverage."""

from unittest.mock import Mock, patch

import grpc
import pytest

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.payment import PaymentConfig


class TestDisperserClientV2FullFinal:
    """Final tests for missing lines in DisperserClientV2Full."""

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

    def test_get_blob_status_success_lines_228_245(self, client):
        """Test get_blob_status success."""
        # Mock the stub
        mock_response = Mock()
        mock_response.status = 4  # COMPLETE
        mock_response.info = Mock()

        with patch.object(client, "_connect"):
            with patch.object(client, "_stub") as mock_stub:
                mock_stub.GetBlobStatus.return_value = mock_response

                # Call the method with hex string
                blob_key_hex = "abcd" * 16  # 64 hex chars = 32 bytes
                result = client.get_blob_status(blob_key_hex)

                # Verify the response is returned
                assert result == mock_response
                assert result.status == 4

            # Verify the response is returned (line 245)
            assert result == mock_response

    def test_get_blob_status_grpc_error_lines_247_248(self, client):
        """Test get_blob_status gRPC error to cover lines 247-248."""
        # Mock the stub
        with patch.object(client, "_stub") as mock_stub:
            # Mock gRPC error
            mock_error = grpc.RpcError()
            mock_error.code = Mock(return_value=grpc.StatusCode.NOT_FOUND)
            mock_error.details = Mock(return_value="Blob not found")
            mock_stub.GetBlobStatus.side_effect = mock_error

            # Ensure client is connected
            client._connected = True

            # Import grpc in the client's namespace if needed
            import grpc as grpc_module

            # Patch disperser_v2_pb2 to have BlobStatusRequest
            with patch("eigenda.client_v2_full.disperser_v2_pb2") as mock_pb2:
                mock_pb2.BlobStatusRequest = Mock(return_value=Mock())

                # Also need to patch grpc in client module
                with patch("eigenda.client_v2_full.grpc", grpc_module):
                    # Call the method and expect exception
                    with pytest.raises(Exception) as exc_info:
                        client.get_blob_status("00" * 32)

                    # Verify error message (line 248)
                    assert "gRPC error" in str(exc_info.value)
                    assert "Blob not found" in str(exc_info.value)
