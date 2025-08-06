"""Test suite for reservation parity with Go client."""

import time
from typing import Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.core import meterer
from eigenda.core.types import (
    PaymentQuorumConfig,
    PaymentQuorumProtocolConfig,
    PaymentType,
    PeriodRecord,
    QuorumID,
    ReservedPayment,
)
from eigenda.payment import PaymentConfig, ReservationAccountant


class TestMetererFunctions:
    """Test meterer utility functions."""

    def test_within_time(self):
        """Test time range validation."""
        from datetime import datetime

        start = datetime(2025, 1, 1, 0, 0, 0)
        end = datetime(2025, 1, 31, 23, 59, 59)

        # Test within range
        test_time = datetime(2025, 1, 15, 12, 0, 0)
        assert meterer.within_time(test_time, start, end) is True

        # Test at boundaries
        assert meterer.within_time(start, start, end) is True
        assert meterer.within_time(end, start, end) is True

        # Test outside range
        before = datetime(2024, 12, 31, 23, 59, 59)
        after = datetime(2025, 2, 1, 0, 0, 0)
        assert meterer.within_time(before, start, end) is False
        assert meterer.within_time(after, start, end) is False

    def test_is_reservation_active(self):
        """Test reservation active check."""
        reservation = ReservedPayment(
            symbols_per_second=1000,
            start_timestamp=1735689600,  # 2025-01-01 00:00:00
            end_timestamp=1738368000,  # 2025-01-31 23:59:59
            quorum_numbers=[0, 1],
            quorum_splits=b"",
        )

        # Within range
        assert meterer.is_reservation_active(reservation, 1736000000) is True

        # Outside range
        assert meterer.is_reservation_active(reservation, 1730000000) is False
        assert meterer.is_reservation_active(reservation, 1740000000) is False

    def test_get_reservation_period_by_nanosecond(self):
        """Test period calculation from nanoseconds."""
        # 1 hour window = 3600 seconds
        window_seconds = 3600

        # Test exact period boundary
        timestamp_ns = 7200_000_000_000  # 2 hours in nanoseconds
        period = meterer.get_reservation_period_by_nanosecond(timestamp_ns, window_seconds)
        assert period == 2

        # Test within period
        timestamp_ns = 5400_000_000_000  # 1.5 hours in nanoseconds
        period = meterer.get_reservation_period_by_nanosecond(timestamp_ns, window_seconds)
        assert period == 1

    def test_get_bin_index(self):
        """Test bin index calculation."""
        # With default 3 bins
        assert meterer.get_bin_index(0) == 0
        assert meterer.get_bin_index(1) == 1
        assert meterer.get_bin_index(2) == 2
        assert meterer.get_bin_index(3) == 0  # Wraps around
        assert meterer.get_bin_index(4) == 1

        # With custom bins
        assert meterer.get_bin_index(7, 5) == 2

    def test_symbols_charged(self):
        """Test symbol charging with minimum."""
        # Below minimum
        assert meterer.symbols_charged(100, 4096) == 4096

        # Above minimum
        assert meterer.symbols_charged(5000, 4096) == 5000

    def test_payment_charged(self):
        """Test payment calculation."""
        num_symbols = 4096
        price_per_symbol = 447000000  # 447 gwei

        expected = num_symbols * price_per_symbol
        assert meterer.payment_charged(num_symbols, price_per_symbol) == expected

    def test_timestamp_conversions(self):
        """Test timestamp conversion functions."""
        # Test nanoseconds to seconds
        ns = 1_500_000_000_000
        assert meterer.nanoseconds_to_seconds(ns) == 1500

        # Test seconds to nanoseconds
        s = 1500
        assert meterer.seconds_to_nanoseconds(s) == 1_500_000_000_000

    def test_validate_timestamp_range(self):
        """Test timestamp range validation."""
        start_s = 1000
        end_s = 2000

        # Within range
        timestamp_ns = 1_500_000_000_000
        is_valid, error = meterer.validate_timestamp_range(timestamp_ns, start_s, end_s)
        assert is_valid is True
        assert error == ""

        # Before range
        timestamp_ns = 500_000_000_000
        is_valid, error = meterer.validate_timestamp_range(timestamp_ns, start_s, end_s)
        assert is_valid is False
        assert "before reservation start" in error

        # After range
        timestamp_ns = 2_500_000_000_000
        is_valid, error = meterer.validate_timestamp_range(timestamp_ns, start_s, end_s)
        assert is_valid is False
        assert "after reservation end" in error

    def test_get_reservation_bin_limit(self):
        """Test bin limit calculation."""
        symbols_per_second = 1000
        window_seconds = 3600  # 1 hour

        # Default 3 bins
        limit = meterer.get_reservation_bin_limit(symbols_per_second, window_seconds)
        assert limit == 1000 * 3600 * 3

    def test_is_within_advance_window(self):
        """Test advance window check."""
        reservation_start = 2000
        advance_window = 300  # 5 minutes

        # Within advance window
        assert meterer.is_within_advance_window(1800, reservation_start, advance_window) is True
        assert meterer.is_within_advance_window(1701, reservation_start, advance_window) is True

        # Too early
        assert meterer.is_within_advance_window(1600, reservation_start, advance_window) is False

        # Already active
        assert meterer.is_within_advance_window(2001, reservation_start, advance_window) is True


class TestReservationValidation:
    """Test reservation validation functions."""

    def test_validate_reservations_success(self):
        """Test successful reservation validation."""
        reservations = {
            0: ReservedPayment(
                symbols_per_second=1000,
                start_timestamp=1000,
                end_timestamp=2000,
                quorum_numbers=[0],
                quorum_splits=b"",
            ),
            1: ReservedPayment(
                symbols_per_second=2000,
                start_timestamp=1000,
                end_timestamp=2000,
                quorum_numbers=[1],
                quorum_splits=b"",
            ),
        }

        quorum_configs = {
            0: PaymentQuorumProtocolConfig(
                min_num_symbols=4096,
                reservation_advance_window=300,
                reservation_rate_limit_window=3600,
                on_demand_rate_limit_window=3600,
                on_demand_enabled=True,
            ),
            1: PaymentQuorumProtocolConfig(
                min_num_symbols=4096,
                reservation_advance_window=300,
                reservation_rate_limit_window=3600,
                on_demand_rate_limit_window=3600,
                on_demand_enabled=True,
            ),
        }

        # Valid request
        error = meterer.validate_reservations(
            reservations,
            quorum_configs,
            [0, 1],
            1_500_000_000_000,  # Within range
            1_500_000_000_000,
        )
        assert error is None

    def test_validate_reservations_missing_quorum(self):
        """Test validation with missing quorum."""
        reservations = {
            0: ReservedPayment(
                symbols_per_second=1000,
                start_timestamp=1000,
                end_timestamp=2000,
                quorum_numbers=[0],
                quorum_splits=b"",
            )
        }

        quorum_configs = {}

        error = meterer.validate_reservations(
            reservations,
            quorum_configs,
            [0, 1],  # Requesting quorum 1 which doesn't exist
            1_500_000_000_000,
            1_500_000_000_000,
        )
        assert error == "no reservation for quorum 1"

    def test_validate_reservation_period(self):
        """Test reservation period validation."""
        reservation = ReservedPayment(
            symbols_per_second=1000,
            start_timestamp=1000,
            end_timestamp=2000,
            quorum_numbers=[0],
            quorum_splits=b"",
        )

        period_records = []
        timestamp_ns = 1_500_000_000_000
        window_seconds = 3600
        symbols_to_charge = 1000

        # Should succeed with empty records
        is_valid, error, period_record = meterer.validate_reservation_period(
            reservation, period_records, timestamp_ns, window_seconds, symbols_to_charge
        )
        assert is_valid is True
        assert error == ""
        assert period_record is not None

    def test_update_period_record(self):
        """Test period record updates."""
        period_records = []

        # Add first record
        updated = meterer.update_period_record(period_records, 1, 1000)
        assert len(updated) == 1
        assert updated[0].index == 1
        assert updated[0].usage == 1000

        # Update existing bin
        updated = meterer.update_period_record(updated, 4, 500)  # Same bin as period 1
        assert len(updated) == 1
        assert updated[0].index == 4
        assert updated[0].usage == 1500

        # Add to different bin
        updated = meterer.update_period_record(updated, 2, 2000)
        assert len(updated) == 2


class TestReservationAccountant:
    """Test ReservationAccountant class."""

    def setup_method(self):
        """Set up test data."""
        self.reservations = {
            0: ReservedPayment(
                symbols_per_second=1000,
                start_timestamp=int(time.time()) - 3600,  # Started 1 hour ago
                end_timestamp=int(time.time()) + 3600,  # Ends in 1 hour
                quorum_numbers=[0],
                quorum_splits=b"",
            )
        }

        self.quorum_configs = {
            0: PaymentQuorumProtocolConfig(
                min_num_symbols=4096,
                reservation_advance_window=300,
                reservation_rate_limit_window=3600,
                on_demand_rate_limit_window=3600,
                on_demand_enabled=True,
            ),
            1: PaymentQuorumProtocolConfig(
                min_num_symbols=4096,
                reservation_advance_window=300,
                reservation_rate_limit_window=3600,
                on_demand_rate_limit_window=3600,
                on_demand_enabled=True,
            ),
        }

        self.payment_configs = {
            0: PaymentQuorumConfig(
                reservation_symbols_per_second=1000,
                on_demand_symbols_per_second=1000,
                on_demand_price_per_symbol=447000000,
            ),
            1: PaymentQuorumConfig(
                reservation_symbols_per_second=0,
                on_demand_symbols_per_second=1000,
                on_demand_price_per_symbol=447000000,
            ),
        }

        self.on_demand_quorums = [0, 1]
        self.payment_config = PaymentConfig()

    def test_accountant_initialization(self):
        """Test accountant initialization."""
        accountant = ReservationAccountant(
            "0x1234567890123456789012345678901234567890",
            self.reservations,
            self.quorum_configs,
            self.payment_configs,
            self.on_demand_quorums,
            self.payment_config,
        )

        assert accountant.account_id == "0x1234567890123456789012345678901234567890"
        assert len(accountant.reservations) == 1
        assert accountant.cumulative_payment == 0

    def test_reservation_payment(self):
        """Test successful reservation payment."""
        accountant = ReservationAccountant(
            "0x1234567890123456789012345678901234567890",
            self.reservations,
            self.quorum_configs,
            self.payment_configs,
            self.on_demand_quorums,
            self.payment_config,
        )

        # Use reservation for quorum 0
        data_len = 100_000  # Encoded blob size
        quorum_numbers = [0]
        timestamp_ns = int(time.time() * 1e9)

        payment_bytes, payment_type, increment = accountant.account_blob(
            data_len, quorum_numbers, timestamp_ns
        )

        assert payment_bytes == b""  # Empty for reservation
        assert payment_type == PaymentType.RESERVATION
        assert increment == 0

    def test_on_demand_fallback(self):
        """Test fallback to on-demand when no reservation."""
        accountant = ReservationAccountant(
            "0x1234567890123456789012345678901234567890",
            self.reservations,
            self.quorum_configs,
            self.payment_configs,
            self.on_demand_quorums,
            self.payment_config,
        )

        # Use quorum 1 which has no reservation
        data_len = 100_000
        quorum_numbers = [1]
        timestamp_ns = int(time.time() * 1e9)

        payment_bytes, payment_type, increment = accountant.account_blob(
            data_len, quorum_numbers, timestamp_ns
        )

        assert payment_bytes != b""  # Has payment for on-demand
        assert payment_type == PaymentType.ON_DEMAND
        assert increment > 0

    def test_mixed_quorums(self):
        """Test request with both reservation and on-demand quorums."""
        accountant = ReservationAccountant(
            "0x1234567890123456789012345678901234567890",
            self.reservations,
            self.quorum_configs,
            self.payment_configs,
            self.on_demand_quorums,
            self.payment_config,
        )

        # Request both quorums - should fall back to on-demand
        data_len = 100_000
        quorum_numbers = [0, 1]
        timestamp_ns = int(time.time() * 1e9)

        payment_bytes, payment_type, increment = accountant.account_blob(
            data_len, quorum_numbers, timestamp_ns
        )

        assert payment_bytes != b""
        assert payment_type == PaymentType.ON_DEMAND
        assert increment > 0

    def test_period_record_tracking(self):
        """Test that period records are properly tracked."""
        accountant = ReservationAccountant(
            "0x1234567890123456789012345678901234567890",
            self.reservations,
            self.quorum_configs,
            self.payment_configs,
            self.on_demand_quorums,
            self.payment_config,
        )

        # Make multiple reservation payments
        data_len = 100_000
        quorum_numbers = [0]
        timestamp_ns = int(time.time() * 1e9)

        # First payment
        accountant.account_blob(data_len, quorum_numbers, timestamp_ns)
        records = accountant.get_period_records(0)
        assert len(records) == 1
        first_usage = records[0].usage
        assert first_usage > 0

        # Second payment
        accountant.account_blob(data_len, quorum_numbers, timestamp_ns)
        records = accountant.get_period_records(0)
        assert len(records) == 1
        assert records[0].usage == first_usage * 2  # Should double


class TestDisperserClientV2FullReservations:
    """Test DisperserClientV2Full with reservation support."""

    @pytest.fixture
    def mock_signer(self):
        """Create mock signer."""
        signer = Mock(spec=LocalBlobRequestSigner)
        signer.get_account_id.return_value = "0x1234567890123456789012345678901234567890"
        signer.sign_payment_state_request.return_value = b"mock_signature"
        return signer

    @pytest.fixture
    def client(self, mock_signer):
        """Create client with mocked dependencies."""
        with patch("eigenda.client_v2.grpc.insecure_channel"), patch(
            "eigenda.client_v2.disperser_v2_pb2_grpc.DisperserStub"
        ):
            client = DisperserClientV2Full(
                hostname="test.eigenda.xyz",
                port=443,
                use_secure_grpc=True,
                signer=mock_signer,
                payment_config=PaymentConfig(),
                use_advanced_reservations=True,
            )
            return client

    def test_advanced_reservations_enabled(self, client):
        """Test that advanced reservations are enabled."""
        assert client.use_advanced_reservations is True
        assert client._reservations == {}
        assert client._quorum_configs == {}

    def test_get_payment_state_for_all_quorums(self, client):
        """Test getting payment state for all quorums."""
        # Mock the gRPC stub
        mock_stub = Mock()
        mock_response = Mock()
        mock_stub.GetPaymentStateForAllQuorums.return_value = mock_response
        client._stub = mock_stub
        client._connected = True

        result = client.get_payment_state_for_all_quorums()

        assert result == mock_response
        mock_stub.GetPaymentStateForAllQuorums.assert_called_once()

    def test_process_advanced_payment_state(self, client):
        """Test processing advanced payment state."""
        # Create mock response
        mock_response = Mock()
        mock_response.quorum_reservations = {
            0: Mock(symbols_per_second=1000, start_timestamp=1000, end_timestamp=2000)
        }
        mock_response.quorum_configs = {
            0: Mock(
                min_num_symbols=4096,
                reservation_advance_window=300,
                reservation_rate_limit_window=3600,
                on_demand_rate_limit_window=3600,
                on_demand_enabled=True,
                reservation_symbols_per_second=1000,
                on_demand_symbols_per_second=1000,
                on_demand_price_per_symbol=447000000,
            )
        }
        mock_response.cumulative_payment = b"\x00\x00\x00\x00"

        client._payment_state_all_quorums = mock_response
        client._process_advanced_payment_state()

        # Check state was parsed correctly
        assert len(client._reservations) == 1
        assert 0 in client._reservations
        assert client._reservations[0].symbols_per_second == 1000
        assert len(client._quorum_configs) == 1
        assert len(client._payment_configs) == 1
        assert 0 in client._on_demand_quorums
        assert isinstance(client.accountant, ReservationAccountant)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
