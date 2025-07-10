"""Simple working tests for client_v2.py to achieve better coverage."""

import pytest
import grpc
from unittest.mock import Mock, patch
from eigenda.client_v2 import DisperserClientV2
from eigenda.core.types import BlobStatus, BlobKey
from eigenda.auth.signer import LocalBlobRequestSigner


class TestDisperserClientV2Simple:
    """Simple tests that actually work for DisperserClientV2."""

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

    def test_parse_blob_status_all_cases(self, client):
        """Test _parse_blob_status for all enum values."""
        # Test the actual mapping that's implemented in the code
        # The mapping now matches the protobuf v2 enum values

        # Test all status mappings as implemented
        assert client._parse_blob_status(0) == BlobStatus.UNKNOWN
        assert client._parse_blob_status(1) == BlobStatus.QUEUED
        assert client._parse_blob_status(2) == BlobStatus.ENCODED
        assert client._parse_blob_status(3) == BlobStatus.GATHERING_SIGNATURES
        assert client._parse_blob_status(4) == BlobStatus.COMPLETE
        assert client._parse_blob_status(5) == BlobStatus.FAILED

        # Test unknown status
        assert client._parse_blob_status(999) == BlobStatus.UNKNOWN
        assert client._parse_blob_status(-1) == BlobStatus.UNKNOWN

    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    def test_get_blob_status_lines_165_181(self, mock_stub_class, client):
        """Test get_blob_status to cover lines 165-181."""
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Create a proper mock response
        mock_response = Mock()
        mock_response.status = 4  # COMPLETE (was 3 in old mapping)
        mock_response.info = Mock()
        mock_response.info.blob_header = Mock()
        mock_response.info.blob_header.commitment = Mock()
        mock_stub.GetBlobStatus.return_value = mock_response

        client._connect()

        # Test with valid blob key
        blob_key = BlobKey(b'test' * 8)  # 32 bytes
        status = client.get_blob_status(blob_key)

        assert status == BlobStatus.COMPLETE

        # Now test gRPC error
        mock_error = grpc.RpcError()
        mock_error.code = Mock(return_value=grpc.StatusCode.NOT_FOUND)
        mock_error.details = Mock(return_value="Blob not found")
        mock_stub.GetBlobStatus.side_effect = mock_error

        with pytest.raises(Exception) as exc_info:
            client.get_blob_status(blob_key)

        assert "gRPC error" in str(exc_info.value)
        assert "Blob not found" in str(exc_info.value)

    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    def test_get_blob_commitment_lines_193_207(self, mock_stub_class, client):
        """Test get_blob_commitment to cover lines 193-207."""
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

        client._connect()
        result = client.get_blob_commitment(b'test data')

        assert result == mock_response

        # Test gRPC error
        mock_error = grpc.RpcError()
        mock_error.code = Mock(return_value=grpc.StatusCode.INTERNAL)
        mock_error.details = Mock(return_value="Internal error")
        mock_stub.GetBlobCommitment.side_effect = mock_error

        with pytest.raises(Exception) as exc_info:
            client.get_blob_commitment(b'test data')

        assert "gRPC error" in str(exc_info.value)
        assert "Internal error" in str(exc_info.value)

    @patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub')
    def test_get_payment_state_lines_219_243(self, mock_stub_class, client):
        """Test get_payment_state to cover lines 219-243."""
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub

        # Mock response
        mock_response = Mock()
        mock_response.reservation = Mock(start_timestamp=1000, end_timestamp=2000)
        mock_response.cumulative_payment = b'\x00' * 32
        mock_stub.GetPaymentState.return_value = mock_response

        client._connect()

        # Test without timestamp (uses current time)
        result = client.get_payment_state()
        assert result == mock_response

        # Test with explicit timestamp
        timestamp = 1234567890000000000
        result = client.get_payment_state(timestamp)
        assert result == mock_response

        # Verify the request
        call_args = mock_stub.GetPaymentState.call_args
        request = call_args[0][0]
        assert request.timestamp == timestamp

        # Test gRPC error
        mock_error = grpc.RpcError()
        mock_error.code = Mock(return_value=grpc.StatusCode.UNAUTHENTICATED)
        mock_error.details = Mock(return_value="Invalid auth")
        mock_stub.GetPaymentState.side_effect = mock_error

        with pytest.raises(Exception) as exc_info:
            client.get_payment_state()

        assert "gRPC error" in str(exc_info.value)
        assert "Invalid auth" in str(exc_info.value)

    def test_create_blob_header_lines_279_297(self, client):
        """Test _create_blob_header to cover lines 279-297."""
        # Create a mock blob commitment
        mock_commitment = Mock()
        mock_commitment.commitment = b'c' * 32
        mock_commitment.length_commitment = b'l' * 32
        mock_commitment.length_proof = b'p' * 32
        mock_commitment.length = 1000

        # Mock time to get consistent timestamp
        with patch('eigenda.client_v2.time.time', return_value=1234567890):
            # Mock the protobuf classes to avoid import issues
            with patch('eigenda.client_v2.common_v2_pb2') as mock_pb2:
                # Create mock classes that accept keyword arguments
                mock_payment_header = Mock()
                mock_blob_header = Mock()

                def create_payment_header(**kwargs):
                    mock_payment_header.account_id = kwargs['account_id']
                    mock_payment_header.timestamp = kwargs['timestamp']
                    mock_payment_header.cumulative_payment = kwargs['cumulative_payment']
                    return mock_payment_header

                def create_blob_header(**kwargs):
                    mock_blob_header.version = kwargs['version']
                    mock_blob_header.commitment = kwargs['commitment']
                    mock_blob_header.quorum_numbers = kwargs['quorum_numbers']
                    mock_blob_header.payment_header = kwargs['payment_header']
                    return mock_blob_header

                mock_pb2.PaymentHeader = create_payment_header
                mock_pb2.BlobHeader = create_blob_header

                # Call the method
                header = client._create_blob_header(
                    blob_version=0,
                    blob_commitment=mock_commitment,
                    quorum_numbers=bytes([0, 1, 2])  # Must be bytes
                )

                # Verify the header was created correctly
                assert header.version == 0
                assert header.commitment == mock_commitment
                assert header.quorum_numbers == bytes([0, 1, 2])
                assert header.payment_header.account_id == client.signer.get_account_id()
                assert header.payment_header.timestamp == 1234567890000000000
                assert header.payment_header.cumulative_payment == b''
