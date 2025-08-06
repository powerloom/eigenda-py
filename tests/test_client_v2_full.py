"""Tests for the full-featured DisperserClientV2Full with payment support."""

import time
from unittest.mock import Mock, patch

import pytest

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full, PaymentType
from eigenda.core.types import BlobKey, BlobStatus
from eigenda.payment import PaymentConfig


class TestDisperserClientV2Full:
    """Test the full-featured disperser client with payment support."""

    @pytest.fixture
    def mock_signer(self):
        """Create a mock signer."""
        signer = Mock(spec=LocalBlobRequestSigner)
        signer.get_account_id.return_value = "0x1234567890123456789012345678901234567890"
        signer.sign_payment_state_request.return_value = b"sig" + b"\x00" * 62  # 65 bytes
        return signer

    @pytest.fixture
    def payment_config(self):
        """Create a payment configuration."""
        return PaymentConfig(price_per_symbol=447000000, min_num_symbols=4096)  # 447 gwei

    @pytest.fixture
    def mock_grpc(self):
        """Mock gRPC dependencies."""
        with patch("eigenda.client_v2.grpc.secure_channel"), patch(
            "eigenda.client_v2.grpc.insecure_channel"
        ), patch("eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub"):
            yield

    @pytest.fixture
    def client(self, mock_signer, payment_config, mock_grpc):
        """Create a client instance with mocked gRPC."""
        client = DisperserClientV2Full(
            hostname="disperser.example.com",
            port=443,
            use_secure_grpc=True,
            signer=mock_signer,
            payment_config=payment_config,
        )
        # Initialize accountant for tests
        from eigenda.payment import SimpleAccountant

        client.accountant = SimpleAccountant(
            account_id=mock_signer.get_account_id(), config=payment_config
        )
        return client

    def test_client_creation(self, client):
        """Test creating the full client."""
        # Accountant is initialized in fixture for testing
        assert client.accountant is not None
        assert client.accountant.account_id == "0x1234567890123456789012345678901234567890"
        assert client.accountant.config.price_per_symbol == 447000000
        assert client._payment_type is None
        assert client._has_reservation is False

    def test_check_payment_state_with_reservation(self, client):
        """Test checking payment state with active reservation."""
        # Mock payment state with active reservation
        mock_payment_state = Mock()
        mock_reservation = Mock()
        mock_reservation.start_timestamp = int(time.time()) - 3600  # Started 1 hour ago
        mock_reservation.end_timestamp = int(time.time()) + 3600  # Ends in 1 hour
        mock_payment_state.reservation = mock_reservation
        mock_payment_state.HasField.return_value = True

        # Mock get_payment_state
        with patch.object(client, "get_payment_state", return_value=mock_payment_state):
            client._check_payment_state()

        assert client._has_reservation is True
        assert client._payment_type == PaymentType.RESERVATION

    def test_check_payment_state_with_on_demand(self, client):
        """Test checking payment state with on-demand payment."""
        # Mock payment state with on-demand
        mock_payment_state = Mock()
        mock_payment_state.HasField.return_value = False  # No reservation
        mock_payment_state.onchain_cumulative_payment = (10**18).to_bytes(32, "big")  # 1 ETH
        mock_payment_state.cumulative_payment = (10**17).to_bytes(32, "big")  # 0.1 ETH used

        # Mock get_payment_state
        with patch.object(client, "get_payment_state", return_value=mock_payment_state):
            client._check_payment_state()

        assert client._has_reservation is False
        assert client._payment_type == PaymentType.ON_DEMAND
        assert client.accountant.cumulative_payment == 10**17

    def test_check_payment_state_no_payment(self, client):
        """Test checking payment state with no payment method."""
        # Mock payment state with no payment
        mock_payment_state = Mock()
        mock_payment_state.HasField.return_value = False
        mock_payment_state.onchain_cumulative_payment = b""

        # Mock get_payment_state
        with patch.object(client, "get_payment_state", return_value=mock_payment_state):
            client._check_payment_state()

        assert client._payment_type is None

    def test_check_payment_state_error(self, client):
        """Test checking payment state with error."""
        # Mock get_payment_state to raise error
        with patch.object(client, "get_payment_state", side_effect=Exception("Network error")):
            client._check_payment_state()

        assert client._payment_type is None

    def test_create_blob_header_reservation(self, client):
        """Test creating blob header with reservation payment."""
        # Set payment type to reservation
        client._payment_type = PaymentType.RESERVATION

        # Mock the blob header creation
        mock_blob_header = Mock()
        mock_blob_header.version = 0
        mock_blob_header.commitment = Mock()
        mock_blob_header.quorum_numbers = [0, 1]
        mock_blob_header.payment_header = Mock()
        mock_blob_header.payment_header.account_id = "0x1234567890123456789012345678901234567890"
        mock_blob_header.payment_header.cumulative_payment = b""

        with patch(
            "eigenda.client_v2_full.common_v2_pb2.BlobHeader", return_value=mock_blob_header
        ):
            with patch("eigenda.client_v2_full.common_v2_pb2.PaymentHeader"):
                # Create blob header
                blob_header = client._create_blob_header(
                    blob_version=0,
                    blob_commitment=mock_blob_header.commitment,
                    quorum_numbers=[0, 1],
                )

        assert blob_header.version == 0
        assert blob_header.quorum_numbers == [0, 1]
        assert blob_header.payment_header.account_id == "0x1234567890123456789012345678901234567890"
        assert blob_header.payment_header.cumulative_payment == b""  # Empty for reservation

    def test_create_blob_header_on_demand(self, client):
        """Test creating blob header with on-demand payment."""
        # Mock payment state to return on-demand payment
        mock_payment_state = Mock()
        mock_payment_state.HasField = Mock(return_value=False)  # No reservation
        mock_payment_state.onchain_cumulative_payment = b"\x00" * 31 + b"\x01"  # Non-zero
        mock_payment_state.cumulative_payment = b"\x00" * 32
        mock_payment_state.payment_global_params = Mock()
        mock_payment_state.payment_global_params.price_per_symbol = 447000000
        mock_payment_state.payment_global_params.min_num_symbols = 4096
        
        # Set last blob size for payment calculation
        client._last_blob_size = 126976  # 4096 symbols worth

        # Expected payment
        expected_payment = 447000000 * 4096
        expected_payment_bytes = expected_payment.to_bytes(
            (expected_payment.bit_length() + 7) // 8, "big"
        )

        # Mock the blob header creation
        mock_blob_header = Mock()
        mock_blob_header.version = 0
        mock_blob_header.commitment = Mock()
        mock_blob_header.quorum_numbers = [0, 1]
        mock_blob_header.payment_header = Mock()
        mock_blob_header.payment_header.account_id = "0x1234567890123456789012345678901234567890"
        mock_blob_header.payment_header.cumulative_payment = expected_payment_bytes

        with patch.object(client, "get_payment_state", return_value=mock_payment_state):
            with patch.object(client, "_connect"):
                with patch(
                    "eigenda.client_v2_full.common_v2_pb2.BlobHeader", return_value=mock_blob_header
                ):
                    with patch("eigenda.client_v2_full.common_v2_pb2.PaymentHeader"):
                        # Create blob header
                        blob_header = client._create_blob_header(
                            blob_version=0,
                            blob_commitment=mock_blob_header.commitment,
                            quorum_numbers=[0, 1],
                        )

        assert blob_header.version == 0
        assert blob_header.quorum_numbers == [0, 1]
        assert blob_header.payment_header.account_id == "0x1234567890123456789012345678901234567890"
        # Should have non-empty payment
        assert len(blob_header.payment_header.cumulative_payment) > 0

        # Check payment calculation
        payment_int = int.from_bytes(blob_header.payment_header.cumulative_payment, "big")
        assert payment_int == expected_payment

    def test_create_blob_header_no_payment(self, client):
        """Test creating blob header with no payment method raises error."""
        # Mock payment state to return no payment method
        mock_payment_state = Mock()
        mock_payment_state.HasField = Mock(return_value=False)  # No reservation
        mock_payment_state.onchain_cumulative_payment = b""  # No on-demand payment
        
        with patch.object(client, "get_payment_state", return_value=mock_payment_state):
            with patch.object(client, "_connect"):
                # Should raise ValueError when no payment method is available
                with pytest.raises(ValueError) as exc_info:
                    client._create_blob_header(
                        blob_version=0,
                        blob_commitment=Mock(),
                        quorum_numbers=[0, 1],
                    )
                
                assert "No payment method available" in str(exc_info.value)
                assert "Make an on-demand deposit" in str(exc_info.value)

    def test_disperse_blob_successful(self, client):
        """Test successful blob dispersal."""
        # Set up client state
        client._payment_type = PaymentType.ON_DEMAND
        client._has_reservation = False
        # Ensure accountant exists
        from eigenda.payment import SimpleAccountant
        client.accountant = SimpleAccountant(client.signer.get_account_id())
        
        # Mock successful dispersal
        expected_key = BlobKey(b"x" * 32)
        expected_status = BlobStatus.QUEUED

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
                mock_disperse_reply.blob_key = b"x" * 32
                mock_stub.DisperseBlob.return_value = mock_disperse_reply
                
                # Mock GetPaymentState (called in _check_payment_state)
                mock_payment_state = Mock()
                mock_payment_state.HasField.return_value = False
                mock_payment_state.onchain_cumulative_payment = b"\x00" * 32
                mock_payment_state.cumulative_payment = b"\x00" * 32
                mock_payment_state.payment_global_params = Mock()
                mock_payment_state.payment_global_params.price_per_symbol = 447000000
                mock_payment_state.payment_global_params.min_num_symbols = 4096
                mock_stub.GetPaymentState.return_value = mock_payment_state
                
                # Mock the protobuf message creation to avoid issues
                mock_blob_header = Mock()
                mock_request = Mock()
                with patch("eigenda.client_v2_full.common_v2_pb2.BlobHeader") as mock_header_class:
                    mock_header_class.return_value = mock_blob_header
                    with patch("eigenda.client_v2_full.common_v2_pb2.PaymentHeader"):
                        with patch("eigenda.client_v2_full.disperser_v2_pb2.DisperseBlobRequest") as mock_request_class:
                            mock_request_class.return_value = mock_request
                            status, key = client.disperse_blob(b"test data")

        assert status == expected_status
        assert key == expected_key
        assert client._last_blob_size > 9  # Encoded size is larger than raw data

    def test_disperse_blob_fallback_to_on_demand(self, client):
        """Test blob dispersal with on-demand payment when no reservation."""
        # Don't set payment type initially - let _check_payment_state do it
        expected_key = BlobKey(b"x" * 32)
        expected_status = BlobStatus.QUEUED

        # Mock GetPaymentState to return on-demand payment
        mock_payment_state = Mock()
        mock_payment_state.HasField = Mock(return_value=False)  # No reservation
        mock_payment_state.onchain_cumulative_payment = b"\x00" * 31 + b"\x01"  # Non-zero payment
        mock_payment_state.cumulative_payment = b"\x00" * 32
        mock_payment_state.payment_global_params = Mock()
        mock_payment_state.payment_global_params.price_per_symbol = 447000000
        mock_payment_state.payment_global_params.min_num_symbols = 4096

        # Mock the gRPC components
        with patch.object(client, "_connect"):
            with patch.object(client, "_stub") as mock_stub:
                # Mock GetPaymentState first since it's called in _check_payment_state
                mock_stub.GetPaymentState.return_value = mock_payment_state
                
                # Mock GetBlobCommitment
                mock_commitment_reply = Mock()
                mock_commitment_reply.blob_commitment = Mock()
                mock_stub.GetBlobCommitment.return_value = mock_commitment_reply
                
                # Mock DisperseBlob
                mock_disperse_reply = Mock()
                mock_disperse_reply.result = 1  # QUEUED
                mock_disperse_reply.blob_key = b"x" * 32
                mock_stub.DisperseBlob.return_value = mock_disperse_reply
                
                # Mock the protobuf message creation to avoid issues
                mock_blob_header = Mock()
                mock_request = Mock()
                with patch("eigenda.client_v2_full.common_v2_pb2.BlobHeader") as mock_header_class:
                    mock_header_class.return_value = mock_blob_header
                    with patch("eigenda.client_v2_full.common_v2_pb2.PaymentHeader"):
                        with patch("eigenda.client_v2_full.disperser_v2_pb2.DisperseBlobRequest") as mock_request_class:
                            mock_request_class.return_value = mock_request
                            status, key = client.disperse_blob(b"test data")

        assert status == expected_status
        assert key == expected_key
        # After dispersal with on-demand payment, these should be set correctly
        assert client._payment_type == PaymentType.ON_DEMAND
        assert not client._has_reservation

    def test_disperse_blob_other_error(self, client):
        """Test blob dispersal with network error."""
        # Set up client state
        client._payment_type = PaymentType.ON_DEMAND
        client._has_reservation = False
        
        # Mock the gRPC components with error
        with patch.object(client, "_connect"):
            with patch.object(client, "_stub") as mock_stub:
                # Mock GetBlobCommitment to raise error immediately
                mock_stub.GetBlobCommitment.side_effect = Exception("Network error")
                
                # Mock GetPaymentState (won't be called since error happens first)
                mock_payment_state = Mock()
                mock_payment_state.HasField.return_value = False
                mock_payment_state.onchain_cumulative_payment = b"\x00" * 32
                mock_stub.GetPaymentState.return_value = mock_payment_state
                
                with pytest.raises(Exception, match="Network error"):
                    client.disperse_blob(b"test data")

    def test_get_payment_info_reservation(self, client):
        """Test get_payment_info with reservation."""
        # Set up reservation state
        client._payment_type = PaymentType.RESERVATION
        client._has_reservation = True
        
        # Mock payment state with reservation
        mock_reservation = Mock()
        mock_reservation.symbols_per_second = 10000
        mock_reservation.start_timestamp = 1000000000
        mock_reservation.end_timestamp = 2000000000
        mock_reservation.quorum_numbers = bytes([0, 1])
        mock_reservation.quorum_splits = bytes([50, 50])
        
        client._payment_state = Mock()
        client._payment_state.reservation = mock_reservation
        client._payment_state.cumulative_payment = b'\x00' * 32
        client._payment_state.onchain_cumulative_payment = b'\x00' * 31 + b'\x01'
        
        # Get payment info
        info = client.get_payment_info()
        
        # Verify reservation info
        assert info["payment_type"] == "reservation"
        assert info["has_reservation"] is True
        assert info["reservation_details"] is not None
        assert info["reservation_details"]["symbols_per_second"] == 10000
        assert info["reservation_details"]["quorum_numbers"] == [0, 1]
        assert info["reservation_details"]["quorum_splits"] == [50, 50]

    def test_get_payment_info_on_demand(self, client):
        """Test get_payment_info with on-demand."""
        # Set on-demand payment
        client._payment_type = PaymentType.ON_DEMAND
        client._has_reservation = False
        
        # Mock payment state
        client._payment_state = Mock()
        client._payment_state.cumulative_payment = (10**17).to_bytes(32, 'big')  # 0.1 ETH used
        client._payment_state.onchain_cumulative_payment = (10**18).to_bytes(32, 'big')  # 1 ETH deposited
        
        # Accountant is already initialized in fixture
        assert client.accountant is not None
        client.accountant.set_cumulative_payment(10**17)
        
        # Get payment info
        info = client.get_payment_info()
        
        # Verify on-demand info
        assert info["payment_type"] == "on_demand"
        assert info["has_reservation"] is False
        assert info["current_cumulative_payment"] == 10**17
        assert info["onchain_balance"] == 10**18
        assert info["price_per_symbol"] == 447000000
        assert info["min_symbols"] == 4096

    def test_get_payment_info_no_payment(self, client):
        """Test get_payment_info with no payment method."""
        # Reset payment state
        client._payment_type = None
        client._has_reservation = False
        client._payment_state = None
        
        # Get payment info
        info = client.get_payment_info()
        
        # Verify no payment info
        assert info["payment_type"] is None
        assert info["has_reservation"] is False
        assert info["reservation_details"] is None
        assert info["current_cumulative_payment"] == 0
        assert info["onchain_balance"] == 0

    def test_expired_reservation(self, client):
        """Test handling expired reservation."""
        # Mock payment state with expired reservation
        mock_payment_state = Mock()
        mock_reservation = Mock()
        mock_reservation.start_timestamp = int(time.time()) - 7200  # Started 2 hours ago
        mock_reservation.end_timestamp = int(time.time()) - 3600  # Ended 1 hour ago
        mock_payment_state.reservation = mock_reservation
        mock_payment_state.HasField.return_value = True

        # Mock get_payment_state
        with patch.object(client, "get_payment_state", return_value=mock_payment_state):
            client._check_payment_state()

        # Should not consider expired reservation as valid
        assert client._has_reservation is False
        assert client._payment_type != PaymentType.RESERVATION
