"""Simple working tests for client_v2_full.py to achieve better coverage."""

import pytest
import grpc
from unittest.mock import Mock, patch
from eigenda.client_v2_full import DisperserClientV2Full, PaymentType
from eigenda.core.types import BlobStatus, BlobKey
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.payment import PaymentConfig


class TestDisperserClientV2FullSimple:
    """Simple tests that actually work for DisperserClientV2Full."""

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

    def test_create_blob_header_line_148(self, client):
        """Test _create_blob_header line 148 - fallback to current cumulative payment."""
        # Set up the payment type as ON_DEMAND but without _last_blob_size
        client._payment_type = PaymentType.ON_DEMAND
        client._has_reservation = False
        client.accountant.cumulative_payment = 123456789

        # Ensure _last_blob_size is not set
        if hasattr(client, '_last_blob_size'):
            delattr(client, '_last_blob_size')

        # Mock _check_payment_state to prevent it from running
        with patch.object(client, '_check_payment_state'):
            # Mock the protobuf classes
            with patch('eigenda.client_v2_full.common_v2_pb2') as mock_pb2:
                mock_blob_commitment = Mock()
                mock_payment_header = Mock()
                mock_blob_header = Mock()

                mock_pb2.PaymentHeader.return_value = mock_payment_header
                mock_pb2.BlobHeader.return_value = mock_blob_header

                # Call the method
                client._create_blob_header(
                    blob_version=0,
                    blob_commitment=mock_blob_commitment,
                    quorum_numbers=[0, 1]
                )

                # Verify payment_bytes was calculated from cumulative_payment (line 148-150)
                call_args = mock_pb2.PaymentHeader.call_args
                assert call_args[1]['cumulative_payment'] == (123456789).to_bytes(4, 'big')

    def test_get_blob_status_full_implementation(self, client):
        """Test get_blob_status that takes hex string (lines 228-248)."""
        # Mock the disperser_v2_pb2 module
        with patch('eigenda.client_v2_full.disperser_v2_pb2') as mock_pb2:
            # Mock BlobStatusRequest
            mock_request = Mock()
            mock_pb2.BlobStatusRequest.return_value = mock_request

            # Mock response
            mock_response = Mock()
            mock_response.status = 3

            # Mock the stub
            with patch.object(client, '_stub') as mock_stub:
                mock_stub.GetBlobStatus.return_value = mock_response

                # Ensure connected
                client._connected = True

                # Test success case
                blob_key_hex = "abcd" * 16  # 64 hex chars
                result = client.get_blob_status(blob_key_hex)

                assert result == mock_response

                # Verify request was created correctly
                mock_pb2.BlobStatusRequest.assert_called_once_with(
                    blob_key=bytes.fromhex(blob_key_hex)
                )

                # Test gRPC error (lines 247-248)
                mock_error = grpc.RpcError()
                mock_error.code = Mock(return_value=grpc.StatusCode.NOT_FOUND)
                mock_error.details = Mock(return_value="Blob not found")
                mock_stub.GetBlobStatus.side_effect = mock_error

                with pytest.raises(Exception) as exc_info:
                    client.get_blob_status(blob_key_hex)

                assert "gRPC error" in str(exc_info.value)
                assert "Blob not found" in str(exc_info.value)

    def test_check_payment_state_various_scenarios(self, client):
        """Test _check_payment_state method with different scenarios."""
        # Test 1: No payment state yet (first call)
        client._payment_state = None

        mock_state = Mock()
        mock_state.reservation.start_timestamp = 1000000000  # Active reservation
        mock_state.reservation.end_timestamp = 2000000000
        mock_state.cumulative_payment = b'\x00' * 32

        with patch.object(client, 'get_payment_state', return_value=mock_state):
            with patch('time.time', return_value=1500000000):  # Within reservation
                client._check_payment_state()

                assert client._payment_type == PaymentType.RESERVATION
                assert client._has_reservation is True

        # Test 2: Expired reservation -> switch to on-demand
        client._payment_state = None

        mock_state.reservation.start_timestamp = 1000000000
        mock_state.reservation.end_timestamp = 1500000000  # Expired
        mock_state.cumulative_payment = b'\x01' + b'\x00' * 31  # Has payment
        mock_state.onchain_cumulative_payment = b'\x01' + b'\x00' * 31  # Has onchain payment

        with patch.object(client, 'get_payment_state', return_value=mock_state):
            with patch('time.time', return_value=1600000000):  # After expiration
                client._check_payment_state()

                assert client._payment_type == PaymentType.ON_DEMAND
                assert client._has_reservation is False
                assert client.accountant.cumulative_payment == 1 << 248

        # Test 3: No reservation, no payment
        client._payment_state = None

        mock_state.reservation.start_timestamp = 0
        mock_state.reservation.end_timestamp = 0
        mock_state.cumulative_payment = b'\x00' * 32
        mock_state.onchain_cumulative_payment = b'\x00' * 32  # No onchain payment

        with patch.object(client, 'get_payment_state', return_value=mock_state):
            client._check_payment_state()

            assert client._payment_type is None
            assert client._has_reservation is False

        # Test 4: gRPC error -> sets payment type to None
        client._payment_state = None

        mock_error = grpc.RpcError()
        mock_error.code = Mock(return_value=grpc.StatusCode.UNAVAILABLE)

        with patch.object(client, 'get_payment_state', side_effect=mock_error):
            client._check_payment_state()

            assert client._payment_type is None
            assert client._payment_state is None

    def test_disperse_blob_retry_on_expired_reservation(self, client):
        """Test disperse_blob retry logic when reservation expires."""
        # Setup initial state
        client._payment_type = PaymentType.RESERVATION
        client._has_reservation = True
        client._payment_state = Mock()

        # First call fails with reservation error
        error = Exception("reservation is not a valid active reservation")

        # Second call succeeds
        expected_status = BlobStatus.PROCESSING
        expected_key = BlobKey(b'y' * 32)

        # Create a counter to track calls
        call_count = 0

        def mock_disperse(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise error
            else:
                return (expected_status, expected_key)

        # Mock parent's disperse_blob
        with patch('eigenda.client_v2.DisperserClientV2.disperse_blob', side_effect=mock_disperse):
            # Mock get_payment_state for the retry
            mock_state = Mock()
            mock_state.reservation.start_timestamp = 0
            mock_state.reservation.end_timestamp = 0
            mock_state.cumulative_payment = b'\x01' + b'\x00' * 31
            mock_state.onchain_cumulative_payment = b'\x01' + b'\x00' * 31  # Has onchain payment

            with patch.object(client, 'get_payment_state', return_value=mock_state):
                with patch('builtins.print'):  # Suppress print statements
                    status, blob_key = client.disperse_blob(b'test data', 0, [0, 1])

                assert status == expected_status
                assert blob_key == expected_key
                assert call_count == 2
                assert client._payment_type == PaymentType.ON_DEMAND
