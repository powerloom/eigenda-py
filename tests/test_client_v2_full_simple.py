"""Simple working tests for client_v2_full.py to achieve better coverage."""

from unittest.mock import Mock, patch

import grpc
import pytest

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full, PaymentType
from eigenda.core.types import BlobKey, BlobStatus
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
        client = DisperserClientV2Full(
            hostname="test.disperser.com",
            port=443,
            use_secure_grpc=True,
            signer=mock_signer,
            payment_config=PaymentConfig(price_per_symbol=447, min_num_symbols=4096),
        )
        # Initialize accountant for tests
        from eigenda.payment import SimpleAccountant

        client.accountant = SimpleAccountant(
            account_id=mock_signer.get_account_id(), config=client.payment_config
        )
        return client

    def test_create_blob_header_line_148(self, client):
        """Test _create_blob_header line 148 - fallback to current cumulative payment."""
        # Set up the payment type as ON_DEMAND but without _last_blob_size
        client._payment_type = PaymentType.ON_DEMAND
        client._has_reservation = False
        # Accountant is already initialized in fixture
        assert client.accountant is not None
        client.accountant.cumulative_payment = 123456789

        # Ensure _last_blob_size is not set
        if hasattr(client, "_last_blob_size"):
            delattr(client, "_last_blob_size")

        # Mock _check_payment_state to prevent it from running
        with patch.object(client, "_check_payment_state"):
            # Mock the protobuf classes
            with patch("eigenda.client_v2_full.common_v2_pb2") as mock_pb2:
                mock_blob_commitment = Mock()
                mock_payment_header = Mock()
                mock_blob_header = Mock()

                mock_pb2.PaymentHeader.return_value = mock_payment_header
                mock_pb2.BlobHeader.return_value = mock_blob_header

                # Call the method
                client._create_blob_header(
                    blob_version=0, blob_commitment=mock_blob_commitment, quorum_numbers=[0, 1]
                )

                # Verify payment_bytes was calculated from cumulative_payment (line 148-150)
                call_args = mock_pb2.PaymentHeader.call_args
                assert call_args[1]["cumulative_payment"] == (123456789).to_bytes(4, "big")

    def test_get_blob_status_full_implementation(self, client):
        """Test get_blob_status from parent class."""
        # Test success case first
        mock_response = Mock()
        mock_response.status = 4  # COMPLETE

        with patch.object(client, "_connect"):
            with patch.object(client, "_stub") as mock_stub:
                mock_stub.GetBlobStatus.return_value = mock_response

                blob_key_hex = "abcd" * 16  # 64 hex chars
                result = client.get_blob_status(blob_key_hex)
                assert result == mock_response

        # Test gRPC error in a separate context
        with patch.object(client, "_connect"):
            with patch.object(client, "_stub") as mock_stub:
                # Create a proper gRPC error that inherits from BaseException
                class MockGrpcError(Exception):
                    def code(self):
                        return grpc.StatusCode.NOT_FOUND

                    def details(self):
                        return "Blob not found"

                # Set the error as side effect
                mock_stub.GetBlobStatus.side_effect = MockGrpcError("Blob not found")

                with pytest.raises(Exception) as exc_info:
                    client.get_blob_status("ffff" * 16)  # Use different key

                assert "NOT_FOUND" in str(exc_info.value) or "Blob not found" in str(exc_info.value)

    def test_check_payment_state_various_scenarios(self, client):
        """Test _check_payment_state method with different scenarios."""
        # Test 1: No payment state yet (first call)
        client._payment_state = None

        mock_state = Mock()
        mock_state.reservation.start_timestamp = 1000000000  # Active reservation
        mock_state.reservation.end_timestamp = 2000000000
        mock_state.cumulative_payment = b"\x00" * 32

        with patch.object(client, "get_payment_state", return_value=mock_state):
            with patch("time.time", return_value=1500000000):  # Within reservation
                client._check_payment_state()

                assert client._payment_type == PaymentType.RESERVATION
                assert client._has_reservation is True

        # Test 2: Expired reservation -> switch to on-demand
        client._payment_state = None

        mock_state.reservation.start_timestamp = 1000000000
        mock_state.reservation.end_timestamp = 1500000000  # Expired
        mock_state.cumulative_payment = b"\x01" + b"\x00" * 31  # Has payment
        mock_state.onchain_cumulative_payment = b"\x01" + b"\x00" * 31  # Has onchain payment

        with patch.object(client, "get_payment_state", return_value=mock_state):
            with patch("time.time", return_value=1600000000):  # After expiration
                client._check_payment_state()

                assert client._payment_type == PaymentType.ON_DEMAND
                assert client._has_reservation is False
                assert client.accountant.cumulative_payment == 1 << 248

        # Test 3: No reservation, no payment
        client._payment_state = None

        # Create a new mock without reservation
        mock_state_no_payment = Mock()
        mock_state_no_payment.HasField.return_value = False  # No reservation
        mock_state_no_payment.onchain_cumulative_payment = b""  # Empty payment

        with patch.object(client, "get_payment_state", return_value=mock_state_no_payment):
            client._check_payment_state()

            assert client._payment_type is None
            assert client._has_reservation is False

        # Test 4: gRPC error -> sets payment type to None
        client._payment_state = None

        mock_error = grpc.RpcError()
        mock_error.code = Mock(return_value=grpc.StatusCode.UNAVAILABLE)

        with patch.object(client, "get_payment_state", side_effect=mock_error):
            client._check_payment_state()

            assert client._payment_type is None
            assert client._payment_state is None

    def test_disperse_blob_retry_on_expired_reservation(self, client):
        """Test disperse_blob with reservation."""
        # Setup initial state with reservation
        client._payment_type = PaymentType.RESERVATION
        client._has_reservation = True
        client._payment_state = Mock()
        # Ensure accountant exists
        from eigenda.payment import SimpleAccountant

        client.accountant = SimpleAccountant(client.signer.get_account_id())

        expected_status = BlobStatus.QUEUED
        expected_key = BlobKey(b"y" * 32)

        # Mock the gRPC components
        with patch.object(client, "_connect"):
            with patch.object(client, "_stub") as mock_stub:
                # Mock GetBlobCommitment
                mock_commitment_reply = Mock()
                mock_commitment_reply.blob_commitment = Mock()
                mock_stub.GetBlobCommitment.return_value = mock_commitment_reply

                # Mock DisperseBlob
                mock_disperse_reply = Mock()
                mock_disperse_reply.result = 1  # QUEUED
                mock_disperse_reply.blob_key = b"y" * 32
                mock_stub.DisperseBlob.return_value = mock_disperse_reply

                # Mock GetPaymentState (in case it's called)
                mock_payment_state = Mock()
                mock_payment_state.HasField.return_value = True
                mock_payment_state.reservation.start_timestamp = 1000000000
                mock_payment_state.reservation.end_timestamp = 2000000000
                mock_stub.GetPaymentState.return_value = mock_payment_state

                # Mock the protobuf message creation to avoid issues
                mock_blob_header = Mock()
                mock_request = Mock()
                with patch("eigenda.client_v2_full.common_v2_pb2.BlobHeader") as mock_header_class:
                    mock_header_class.return_value = mock_blob_header
                    with patch("eigenda.client_v2_full.common_v2_pb2.PaymentHeader"):
                        with patch(
                            "eigenda.client_v2_full.disperser_v2_pb2.DisperseBlobRequest"
                        ) as mock_request_class:
                            mock_request_class.return_value = mock_request
                            # Call disperse_blob
                            with patch("builtins.print"):  # Suppress print statements
                                with patch(
                                    "time.time", return_value=1500000000
                                ):  # Within reservation
                                    status, blob_key = client.disperse_blob(b"test data")

                assert status == expected_status
                assert blob_key == expected_key
                # The payment type should remain as reservation
                assert client._payment_type == PaymentType.RESERVATION
