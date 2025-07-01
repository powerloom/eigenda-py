"""Additional tests for client_v2.py to achieve higher coverage."""

import pytest
import grpc
from unittest.mock import Mock, patch
from eigenda.client_v2 import DisperserClientV2
from eigenda.core.types import BlobStatus, BlobKey
from eigenda.auth.signer import LocalBlobRequestSigner


class TestDisperserClientV2Additional:
    """Additional tests for DisperserClientV2 missing coverage."""

    @pytest.fixture
    def mock_signer(self):
        """Create a mock signer."""
        signer = Mock(spec=LocalBlobRequestSigner)
        signer.get_account_id.return_value = "0x1234567890123456789012345678901234567890"
        signer.sign_blob_request.return_value = b"signature" + b'\x00' * 56  # 65 bytes
        signer.sign_payment_state_request.return_value = b"sig" + b'\x00' * 62  # 65 bytes
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

    def test_parse_blob_status_encoded(self, client):
        """Test _parse_blob_status for ENCODED status."""
        # Mock the disperser_v2_pb2 module
        with patch('eigenda.client_v2.disperser_v2_pb2') as mock_pb2:
            mock_pb2.ENCODED = 2
            # ENCODED maps to GATHERING_SIGNATURES
            assert client._parse_blob_status(2) == BlobStatus.GATHERING_SIGNATURES

    def test_parse_blob_status_certified(self, client):
        """Test _parse_blob_status for CERTIFIED status."""
        with patch('eigenda.client_v2.disperser_v2_pb2') as mock_pb2:
            mock_pb2.CERTIFIED = 3
            # CERTIFIED maps to COMPLETE
            assert client._parse_blob_status(3) == BlobStatus.COMPLETE

    def test_parse_blob_status_failed(self, client):
        """Test _parse_blob_status for FAILED status."""
        with patch('eigenda.client_v2.disperser_v2_pb2') as mock_pb2:
            mock_pb2.FAILED = 4
            assert client._parse_blob_status(4) == BlobStatus.FAILED

    def test_parse_blob_status_insufficient_signatures(self, client):
        """Test _parse_blob_status for INSUFFICIENT_SIGNATURES."""
        with patch('eigenda.client_v2.disperser_v2_pb2') as mock_pb2:
            mock_pb2.INSUFFICIENT_SIGNATURES = 5
            assert client._parse_blob_status(5) == BlobStatus.INSUFFICIENT_SIGNATURES

    def test_parse_blob_status_unknown(self, client):
        """Test _parse_blob_status for unknown status."""
        # Any unmapped status should return UNKNOWN
        assert client._parse_blob_status(999) == BlobStatus.UNKNOWN

    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    def test_get_blob_commitment_success(self, mock_stub_class, client):
        """Test get_blob_commitment method."""
        # Create mock stub
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Create mock response
        mock_response = Mock()
        mock_commitment = Mock()
        mock_commitment.commitment = b'test_commitment'
        mock_commitment.length_commitment = b'test_length_commitment'
        mock_commitment.length_proof = b'test_length_proo'
        mock_commitment.length = 100
        mock_response.blob_commitment = mock_commitment
        mock_stub.GetBlobCommitment.return_value = mock_response

        # Connect and test
        client._connect()
        data = b'test data'
        result = client.get_blob_commitment(data)

        assert result == mock_response
        mock_stub.GetBlobCommitment.assert_called_once()

    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    def test_get_blob_commitment_grpc_error(self, mock_stub_class, client):
        """Test get_blob_commitment with gRPC error."""
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Mock gRPC error
        mock_error = grpc.RpcError()
        mock_error.code = Mock(return_value=grpc.StatusCode.UNAVAILABLE)
        mock_error.details = Mock(return_value="Service unavailable")
        mock_stub.GetBlobCommitment.side_effect = mock_error

        client._connect()

        with pytest.raises(Exception) as exc_info:
            client.get_blob_commitment(b'test data')

        assert "gRPC error" in str(exc_info.value)
        assert "Service unavailable" in str(exc_info.value)

    @patch('eigenda.client_v2.common_v2_pb2')
    @patch('eigenda.client_v2.disperser_v2_pb2')
    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    def test_disperse_blob_complete_flow(
        self, mock_stub_class, mock_disperser_pb2, mock_common_pb2, client
    ):
        """Test complete disperse_blob flow."""
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Mock get_blob_commitment response
        commitment_response = Mock()
        mock_commitment = Mock()
        mock_commitment.commitment = b'commitment'
        mock_commitment.length_commitment = b'length_commitment'
        mock_commitment.length_proof = b'length_proo'
        mock_commitment.length = 100
        commitment_response.blob_commitment = mock_commitment

        # Mock disperse response
        disperse_response = Mock()
        disperse_response.result = 1  # QUEUED
        disperse_response.blob_key = b'x' * 32

        mock_stub.GetBlobCommitment.return_value = commitment_response
        mock_stub.DisperseBlob.return_value = disperse_response

        # Mock protobuf classes
        mock_payment_header = Mock()
        mock_blob_header = Mock()
        mock_common_pb2.PaymentHeader.return_value = mock_payment_header
        mock_common_pb2.BlobHeader.return_value = mock_blob_header

        mock_request = Mock()
        mock_disperser_pb2.DisperseBlobRequest.return_value = mock_request

        # Mock _parse_blob_status
        with patch.object(client, '_parse_blob_status', return_value=BlobStatus.PROCESSING):
            client._connect()

            data = b'test data'
            status, blob_key = client.disperse_blob(data, 0, [0, 1])

            assert status == BlobStatus.PROCESSING
            assert isinstance(blob_key, BlobKey)
            assert bytes(blob_key) == b'x' * 32

    @patch('eigenda.client_v2.common_v2_pb2')
    @patch('eigenda.client_v2.disperser_v2_pb2')
    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    def test_disperse_blob_grpc_error(
        self, mock_stub_class, mock_disperser_pb2, mock_common_pb2, client
    ):
        """Test disperse_blob with gRPC error during dispersal."""
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Mock commitment response
        commitment_response = Mock()
        mock_commitment = Mock()
        mock_commitment.commitment = b'commitment'
        mock_commitment.length_commitment = b'length_commitment'
        mock_commitment.length_proof = b'length_proo'
        mock_commitment.length = 100
        commitment_response.blob_commitment = mock_commitment
        mock_stub.GetBlobCommitment.return_value = commitment_response

        # Mock protobuf classes
        mock_payment_header = Mock()
        mock_blob_header = Mock()
        mock_common_pb2.PaymentHeader.return_value = mock_payment_header
        mock_common_pb2.BlobHeader.return_value = mock_blob_header

        mock_request = Mock()
        mock_disperser_pb2.DisperseBlobRequest.return_value = mock_request

        # Mock gRPC error on DisperseBlob
        mock_error = grpc.RpcError()
        mock_error.code = Mock(return_value=grpc.StatusCode.UNAVAILABLE)
        mock_error.details = Mock(return_value="Service unavailable")
        mock_stub.DisperseBlob.side_effect = mock_error

        client._connect()

        with pytest.raises(Exception) as exc_info:
            client.disperse_blob(b'test data', 0, [0, 1])

        assert "gRPC error" in str(exc_info.value)
        assert "Service unavailable" in str(exc_info.value)

    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    def test_get_blob_status_success(self, mock_stub_class, client):
        """Test get_blob_status method."""
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Mock response
        mock_response = Mock()
        mock_response.status = 3  # CERTIFIED
        mock_response.info = Mock()
        mock_response.info.blob_header = Mock()
        mock_response.info.blob_header.commitment = Mock()
        mock_stub.GetBlobStatus.return_value = mock_response

        # Mock _parse_blob_status
        with patch.object(client, '_parse_blob_status', return_value=BlobStatus.COMPLETE):
            client._connect()

            blob_key = BlobKey(b'test_key' + b'\x00' * 24)
            status = client.get_blob_status(blob_key)

            assert status == BlobStatus.COMPLETE
            mock_stub.GetBlobStatus.assert_called_once()

    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    def test_get_blob_status_grpc_error(self, mock_stub_class, client):
        """Test get_blob_status with gRPC error."""
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Mock gRPC error
        mock_error = grpc.RpcError()
        mock_error.code = Mock(return_value=grpc.StatusCode.NOT_FOUND)
        mock_error.details = Mock(return_value="Blob not found")
        mock_stub.GetBlobStatus.side_effect = mock_error

        client._connect()

        blob_key = BlobKey(b'not_found' + b'\x00' * 23)
        with pytest.raises(Exception) as exc_info:
            client.get_blob_status(blob_key)

        assert "gRPC error" in str(exc_info.value)
        assert "Blob not found" in str(exc_info.value)

    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    def test_get_payment_state_with_timestamp(self, mock_stub_class, client):
        """Test get_payment_state with explicit timestamp."""
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Mock response
        mock_response = Mock()
        mock_response.reservation = Mock(start_timestamp=1000, end_timestamp=2000)
        mock_response.cumulative_payment = b'\x00' * 32
        mock_stub.GetPaymentState.return_value = mock_response

        client._connect()

        timestamp = 1234567890000000000
        result = client.get_payment_state(timestamp)

        assert result == mock_response

        # Verify the request
        call_args = mock_stub.GetPaymentState.call_args
        request = call_args[0][0]
        assert request.timestamp == timestamp

    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    def test_get_payment_state_grpc_error(self, mock_stub_class, client):
        """Test get_payment_state with gRPC error."""
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Mock gRPC error
        mock_error = grpc.RpcError()
        mock_error.code = Mock(return_value=grpc.StatusCode.UNAUTHENTICATED)
        mock_error.details = Mock(return_value="Invalid signature")
        mock_stub.GetPaymentState.side_effect = mock_error

        client._connect()

        with pytest.raises(Exception) as exc_info:
            client.get_payment_state()

        assert "gRPC error" in str(exc_info.value)
        assert "Invalid signature" in str(exc_info.value)

    def test_create_blob_header(self, client):
        """Test _create_blob_header method."""
        # Mock dependencies
        mock_commitment = Mock()
        mock_commitment.commitment = b'c' * 32
        mock_commitment.length_commitment = b'l' * 32
        mock_commitment.length_proof = b'p' * 32
        mock_commitment.length = 1000

        with patch('eigenda.client_v2.common_v2_pb2') as mock_pb2:
            mock_header = Mock()
            mock_pb2.BlobHeader.return_value = mock_header
            mock_pb2.PaymentMetadata.return_value = Mock()

            header = client._create_blob_header(
                blob_version=0,
                blob_commitment=mock_commitment,
                quorum_numbers=[0, 1, 2]
            )

            assert header == mock_header

            # Verify BlobHeader was created with correct params
            mock_pb2.BlobHeader.assert_called_once()
            call_kwargs = mock_pb2.BlobHeader.call_args[1]
            assert call_kwargs['version'] == 0
            assert call_kwargs['commitment'] == mock_commitment
            assert call_kwargs['quorum_numbers'] == [0, 1, 2]

    @patch('eigenda.client_v2.common_v2_pb2')
    @patch('eigenda.client_v2.disperser_v2_pb2')
    def test_disperse_blob_with_custom_timeout(self, mock_disperser_pb2, mock_common_pb2, client):
        """Test disperse_blob with custom timeout."""
        with patch.object(client, 'get_blob_commitment') as mock_commitment:
            with patch.object(client, '_stub') as mock_stub:
                with patch.object(client, '_parse_blob_status', return_value=BlobStatus.PROCESSING):
                    # Setup mocks
                    mock_commitment_obj = Mock()
                    mock_commitment_obj.commitment = b'c' * 32
                    mock_commitment_obj.length_commitment = b'l' * 32
                    mock_commitment_obj.length_proof = b'p' * 32
                    mock_commitment_obj.length = 100
                    mock_commitment.return_value = Mock(blob_commitment=mock_commitment_obj)

                    # Mock protobuf classes
                    mock_payment_header = Mock()
                    mock_blob_header = Mock()
                    mock_common_pb2.PaymentHeader.return_value = mock_payment_header
                    mock_common_pb2.BlobHeader.return_value = mock_blob_header

                    mock_request = Mock()
                    mock_disperser_pb2.DisperseBlobRequest.return_value = mock_request

                    response = Mock()
                    response.result = 1  # QUEUED
                    response.blob_key = b'k' * 32  # 32 bytes
                    mock_stub.DisperseBlob.return_value = response

                    client._connected = True

                    # Test with custom timeout
                    custom_timeout = 60
                    status, blob_key = client.disperse_blob(b'data', 0, [0], timeout=custom_timeout)

                    # Verify timeout was passed
                    call_args = mock_stub.DisperseBlob.call_args
                    assert call_args[1]['timeout'] == custom_timeout
