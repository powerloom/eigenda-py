"""Final tests for client_v2.py to achieve 100% coverage."""

import pytest
import grpc
from unittest.mock import Mock, patch
from eigenda.client_v2 import DisperserClientV2
from eigenda.core.types import BlobStatus, BlobKey
from eigenda.auth.signer import LocalBlobRequestSigner


class TestDisperserClientV2Final:
    """Final tests for missing lines in DisperserClientV2."""

    @pytest.fixture
    def mock_signer(self):
        """Create a mock signer."""
        signer = Mock(spec=LocalBlobRequestSigner)
        signer.get_account_id.return_value = "0x1234567890123456789012345678901234567890"
        signer.sign_blob_request.return_value = b"signature" + b'\x00' * 56  # 65 bytes
        return signer

    @pytest.fixture
    def client(self, mock_signer):
        """Create a test client."""
        return DisperserClientV2(
            hostname="test.disperser.com",
            port=443,
            use_secure_grpc=True,
            signer=mock_signer
        )

    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    @patch('eigenda.client_v2.disperser_v2_pb2')
    @patch('eigenda.client_v2.common_v2_pb2')
    def test_disperse_blob_full_flow_to_cover_lines_128_153(
        self, mock_common_pb2, mock_disperser_pb2, mock_stub_class, client
    ):
        """Test full disperse_blob flow to cover lines 128-153."""
        # Setup mocks
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Mock protobuf classes
        mock_blob_header = Mock()
        mock_payment_metadata = Mock()
        mock_common_pb2.BlobHeader.return_value = mock_blob_header
        mock_common_pb2.PaymentMetadata.return_value = mock_payment_metadata

        # Mock disperser request
        mock_request = Mock()
        mock_disperser_pb2.DisperseBlobRequest.return_value = mock_request

        # Mock blob commitment response
        mock_commitment_response = Mock()
        mock_commitment = Mock()
        mock_commitment.commitment = b'c' * 32
        mock_commitment.length_commitment = b'l' * 32
        mock_commitment.length_proof = b'p' * 32
        mock_commitment.length = 100
        mock_commitment_response.blob_commitment = mock_commitment
        mock_stub.GetBlobCommitment.return_value = mock_commitment_response

        # Mock disperse response
        mock_disperse_response = Mock()
        mock_disperse_response.result = 1  # Some status
        mock_disperse_response.blob_key = b'x' * 32
        mock_stub.DisperseBlob.return_value = mock_disperse_response

        # Mock status enums
        mock_disperser_pb2.QUEUED = 1

        # Connect client
        client._connect()

        # Call disperse_blob
        data = b'test data'
        status, blob_key = client.disperse_blob(data, 0, [0, 1])

        # Verify all the calls were made (lines 128-153)
        client.signer.sign_blob_request.assert_called_once_with(mock_blob_header)
        mock_disperser_pb2.DisperseBlobRequest.assert_called_once_with(
            blob=data,
            blob_header=mock_blob_header,
            signature=client.signer.sign_blob_request.return_value
        )
        mock_stub.DisperseBlob.assert_called_once()

        # Verify result
        assert status == BlobStatus.PROCESSING  # QUEUED maps to PROCESSING
        assert isinstance(blob_key, BlobKey)
        assert bytes(blob_key) == b'x' * 32

    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    @patch('eigenda.client_v2.disperser_v2_pb2')
    @patch('eigenda.client_v2.common_v2_pb2')
    def test_disperse_blob_grpc_error_line_152_153(
        self, mock_common_pb2, mock_disperser_pb2, mock_stub_class, client
    ):
        """Test disperse_blob gRPC error to cover lines 152-153."""
        # Setup mocks
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Mock protobuf classes
        mock_blob_header = Mock()
        mock_payment_metadata = Mock()
        mock_common_pb2.BlobHeader.return_value = mock_blob_header
        mock_common_pb2.PaymentMetadata.return_value = mock_payment_metadata

        # Mock disperser request
        mock_request = Mock()
        mock_disperser_pb2.DisperseBlobRequest.return_value = mock_request

        # Mock blob commitment response
        mock_commitment_response = Mock()
        mock_commitment = Mock()
        mock_commitment.commitment = b'c' * 32
        mock_commitment.length_commitment = b'l' * 32
        mock_commitment.length_proof = b'p' * 32
        mock_commitment.length = 100
        mock_commitment_response.blob_commitment = mock_commitment
        mock_stub.GetBlobCommitment.return_value = mock_commitment_response

        # Mock gRPC error on DisperseBlob
        mock_error = grpc.RpcError()
        mock_error.code = Mock(return_value=grpc.StatusCode.INTERNAL)
        mock_error.details = Mock(return_value="Internal server error")
        mock_stub.DisperseBlob.side_effect = mock_error

        # Connect client
        client._connect()

        # Call disperse_blob and expect exception
        with pytest.raises(Exception) as exc_info:
            client.disperse_blob(b'test data', 0, [0, 1])

        # Verify error message (line 153)
        assert "gRPC error" in str(exc_info.value)
        assert "Internal server error" in str(exc_info.value)

    def test_close_with_channel_lines_248_251(self, client):
        """Test close method with active channel to cover lines 248-251."""
        # Setup active channel
        mock_channel = Mock()
        client._channel = mock_channel
        client._connected = True
        client._stub = Mock()

        # Call close
        client.close()

        # Verify all cleanup was done (lines 248-251)
        mock_channel.close.assert_called_once()
        assert client._connected is False
        assert client._channel is None
        assert client._stub is None
