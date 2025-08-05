"""Tests for the full-featured DisperserClientV2Full with payment support."""

import pytest
from unittest.mock import Mock, patch
import time

from eigenda.client_v2_full import (
    DisperserClientV2Full,
    PaymentType
)
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.payment import PaymentConfig
from eigenda.core.types import BlobStatus, BlobKey


class TestDisperserClientV2Full:
    """Test the full-featured disperser client with payment support."""

    @pytest.fixture
    def mock_signer(self):
        """Create a mock signer."""
        signer = Mock(spec=LocalBlobRequestSigner)
        signer.get_account_id.return_value = "0x1234567890123456789012345678901234567890"
        return signer

    @pytest.fixture
    def payment_config(self):
        """Create a payment configuration."""
        return PaymentConfig(
            price_per_symbol=447000000,  # 447 gwei
            min_num_symbols=4096
        )

    @pytest.fixture
    def mock_grpc(self):
        """Mock gRPC dependencies."""
        with patch('eigenda.client_v2.grpc.secure_channel'), \
                patch('eigenda.client_v2.grpc.insecure_channel'), \
                patch('eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub'):
            yield

    @pytest.fixture
    def client(self, mock_signer, payment_config, mock_grpc):
        """Create a client instance with mocked gRPC."""
        client = DisperserClientV2Full(
            hostname="disperser.example.com",
            port=443,
            use_secure_grpc=True,
            signer=mock_signer,
            payment_config=payment_config
        )
        # Initialize accountant for tests
        from eigenda.payment import SimpleAccountant
        client.accountant = SimpleAccountant(
            account_id=mock_signer.get_account_id(),
            config=payment_config
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
        with patch.object(client, 'get_payment_state', return_value=mock_payment_state):
            client._check_payment_state()

        assert client._has_reservation is True
        assert client._payment_type == PaymentType.RESERVATION

    def test_check_payment_state_with_on_demand(self, client):
        """Test checking payment state with on-demand payment."""
        # Mock payment state with on-demand
        mock_payment_state = Mock()
        mock_payment_state.HasField.return_value = False  # No reservation
        mock_payment_state.onchain_cumulative_payment = (10**18).to_bytes(32, 'big')  # 1 ETH
        mock_payment_state.cumulative_payment = (10**17).to_bytes(32, 'big')  # 0.1 ETH used

        # Mock get_payment_state
        with patch.object(client, 'get_payment_state', return_value=mock_payment_state):
            client._check_payment_state()

        assert client._has_reservation is False
        assert client._payment_type == PaymentType.ON_DEMAND
        assert client.accountant.cumulative_payment == 10**17

    def test_check_payment_state_no_payment(self, client):
        """Test checking payment state with no payment method."""
        # Mock payment state with no payment
        mock_payment_state = Mock()
        mock_payment_state.HasField.return_value = False
        mock_payment_state.onchain_cumulative_payment = b''

        # Mock get_payment_state
        with patch.object(client, 'get_payment_state', return_value=mock_payment_state):
            client._check_payment_state()

        assert client._payment_type is None

    def test_check_payment_state_error(self, client):
        """Test checking payment state with error."""
        # Mock get_payment_state to raise error
        with patch.object(client, 'get_payment_state', side_effect=Exception("Network error")):
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
        mock_blob_header.payment_header.cumulative_payment = b''

        with patch(
            'eigenda.client_v2_full.common_v2_pb2.BlobHeader',
            return_value=mock_blob_header
        ):
            with patch('eigenda.client_v2_full.common_v2_pb2.PaymentHeader'):
                # Create blob header
                blob_header = client._create_blob_header(
                    blob_version=0,
                    blob_commitment=mock_blob_header.commitment,
                    quorum_numbers=[0, 1]
                )

        assert blob_header.version == 0
        assert blob_header.quorum_numbers == [0, 1]
        assert blob_header.payment_header.account_id == "0x1234567890123456789012345678901234567890"
        assert blob_header.payment_header.cumulative_payment == b''  # Empty for reservation

    def test_create_blob_header_on_demand(self, client):
        """Test creating blob header with on-demand payment."""
        # Set payment type to on-demand
        client._payment_type = PaymentType.ON_DEMAND
        client._last_blob_size = 126976  # 4096 symbols worth

        # Expected payment
        expected_payment = 447000000 * 4096
        expected_payment_bytes = expected_payment.to_bytes(
            (expected_payment.bit_length() + 7) // 8, 'big'
        )

        # Mock the blob header creation
        mock_blob_header = Mock()
        mock_blob_header.version = 0
        mock_blob_header.commitment = Mock()
        mock_blob_header.quorum_numbers = [0, 1]
        mock_blob_header.payment_header = Mock()
        mock_blob_header.payment_header.account_id = "0x1234567890123456789012345678901234567890"
        mock_blob_header.payment_header.cumulative_payment = expected_payment_bytes

        with patch(
            'eigenda.client_v2_full.common_v2_pb2.BlobHeader',
            return_value=mock_blob_header
        ):
            with patch('eigenda.client_v2_full.common_v2_pb2.PaymentHeader'):
                # Create blob header
                blob_header = client._create_blob_header(
                    blob_version=0,
                    blob_commitment=mock_blob_header.commitment,
                    quorum_numbers=[0, 1]
                )

        assert blob_header.version == 0
        assert blob_header.quorum_numbers == [0, 1]
        assert blob_header.payment_header.account_id == "0x1234567890123456789012345678901234567890"
        # Should have non-empty payment
        assert len(blob_header.payment_header.cumulative_payment) > 0

        # Check payment calculation
        payment_int = int.from_bytes(blob_header.payment_header.cumulative_payment, 'big')
        assert payment_int == expected_payment

    def test_create_blob_header_no_payment(self, client):
        """Test creating blob header with no payment method."""
        # No payment type set
        client._payment_type = None

        # Mock the blob header creation
        mock_blob_header = Mock()
        mock_blob_header.version = 0
        mock_blob_header.commitment = Mock()
        mock_blob_header.quorum_numbers = [0, 1]
        mock_blob_header.payment_header = Mock()
        mock_blob_header.payment_header.account_id = "0x1234567890123456789012345678901234567890"
        mock_blob_header.payment_header.cumulative_payment = b''

        # Mock payment state check
        with patch.object(client, '_check_payment_state'):
            with patch(
                'eigenda.client_v2_full.common_v2_pb2.BlobHeader',
                return_value=mock_blob_header
            ):
                with patch('eigenda.client_v2_full.common_v2_pb2.PaymentHeader'):
                    # Create blob header
                    blob_header = client._create_blob_header(
                        blob_version=0,
                        blob_commitment=mock_blob_header.commitment,
                        quorum_numbers=[0, 1]
                    )

        assert blob_header.payment_header.cumulative_payment == b''  # Empty when no payment

    def test_disperse_blob_successful(self, client):
        """Test successful blob dispersal."""
        # Mock successful dispersal
        expected_key = BlobKey(b'x' * 32)
        expected_status = BlobStatus.COMPLETE

        with patch.object(DisperserClientV2Full.__bases__[0], 'disperse_blob',
                          return_value=(expected_status, expected_key)):
            status, key = client.disperse_blob(b'test data')

        assert status == expected_status
        assert key == expected_key
        assert client._last_blob_size == 9  # len(b'test data')

    def test_disperse_blob_fallback_to_on_demand(self, client):
        """Test blob dispersal falling back from reservation to on-demand."""
        # Start with reservation payment type
        client._payment_type = PaymentType.RESERVATION

        # Mock reservation failure then success
        expected_key = BlobKey(b'x' * 32)
        expected_status = BlobStatus.COMPLETE

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails with reservation error
                raise Exception("not a valid active reservation for account")
            else:
                # Second call succeeds
                return (expected_status, expected_key)

        with patch.object(DisperserClientV2Full.__bases__[0], 'disperse_blob',
                          side_effect=side_effect):
            with patch.object(client, '_check_payment_state'):
                status, key = client.disperse_blob(b'test data')

        assert status == expected_status
        assert key == expected_key
        assert client._payment_type == PaymentType.ON_DEMAND
        assert not client._has_reservation

    def test_disperse_blob_other_error(self, client):
        """Test blob dispersal with non-reservation error."""
        # Mock dispersal failure
        with patch.object(DisperserClientV2Full.__bases__[0], 'disperse_blob',
                          side_effect=Exception("Network error")):
            with pytest.raises(Exception, match="Network error"):
                client.disperse_blob(b'test data')

    def test_get_payment_info_reservation(self, client):
        """Test getting payment info with reservation."""
        # Set reservation payment
        client._payment_type = PaymentType.RESERVATION
        client._has_reservation = True
        client._payment_state = Mock()  # Avoid check

        info = client.get_payment_info()

        assert info["payment_type"] == "reservation"
        assert info["has_reservation"] is True
        assert "current_cumulative_payment" not in info

    def test_get_payment_info_on_demand(self, client):
        """Test getting payment info with on-demand."""
        # Set on-demand payment
        client._payment_type = PaymentType.ON_DEMAND
        client._has_reservation = False
        client._payment_state = Mock()  # Avoid check
        # Accountant is already initialized in fixture
        assert client.accountant is not None
        client.accountant.set_cumulative_payment(10**18)  # 1 ETH

        info = client.get_payment_info()

        assert info["payment_type"] == "on_demand"
        assert info["has_reservation"] is False
        assert info["current_cumulative_payment"] == 10**18
        assert info["price_per_symbol"] == 447000000
        assert info["min_symbols"] == 4096

    def test_get_payment_info_no_payment(self, client):
        """Test getting payment info with no payment method."""
        # Mock payment state check
        with patch.object(client, '_check_payment_state'):
            info = client.get_payment_info()

        assert info["payment_type"] == "none"
        assert info["has_reservation"] is False
        assert "current_cumulative_payment" not in info

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
        with patch.object(client, 'get_payment_state', return_value=mock_payment_state):
            client._check_payment_state()

        # Should not consider expired reservation as valid
        assert client._has_reservation is False
        assert client._payment_type != PaymentType.RESERVATION
