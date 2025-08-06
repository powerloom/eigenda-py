"""Payment calculation utilities for EigenDA on-demand payments."""

import copy
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from eigenda.core import meterer
from eigenda.core.types import (
    PaymentQuorumConfig,
    PaymentQuorumProtocolConfig,
    PaymentType,
    PeriodRecord,
    QuorumID,
    QuorumPeriodRecords,
    ReservedPayment,
)


@dataclass
class PaymentConfig:
    """Configuration for on-demand payment calculations."""

    price_per_symbol: int = 447000000  # wei per symbol
    min_num_symbols: int = 4096

    def __post_init__(self):
        """Validate configuration."""
        if self.price_per_symbol < 0:
            raise ValueError("price_per_symbol cannot be negative")
        if self.min_num_symbols <= 0:
            raise ValueError("min_num_symbols must be positive")


def get_blob_length_power_of_2(data_len: int) -> int:
    """
    Calculate the number of symbols for a blob, rounding up to power of 2.

    This matches the Go implementation in encoding/utils.go.
    Each symbol is 31 bytes (after removing the padding byte).

    Args:
        data_len: Length of the encoded blob data in bytes

    Returns:
        Number of symbols (power of 2)
    """
    if data_len == 0:
        return 0

    # Each symbol is 31 bytes (after removing padding byte)
    symbols = (data_len + 30) // 31

    # Round up to next power of 2
    if symbols == 0:
        return 1

    # Find next power of 2
    power = 1
    while power < symbols:
        power *= 2

    return power


def calculate_payment_increment(data_len: int, config: Optional[PaymentConfig] = None) -> int:
    """
    Calculate the payment increment for a blob of given size.

    Args:
        data_len: Length of the encoded blob data in bytes
        config: Payment configuration (uses defaults if not provided)

    Returns:
        Payment amount in wei
    """
    if config is None:
        config = PaymentConfig()

    # Get number of symbols (power of 2)
    num_symbols = get_blob_length_power_of_2(data_len)

    # Ensure minimum symbols
    if num_symbols < config.min_num_symbols:
        num_symbols = config.min_num_symbols

    # Calculate payment
    payment = num_symbols * config.price_per_symbol

    return payment


class SimpleAccountant:
    """
    Simple accountant for on-demand payment tracking.

    This implementation handles the basic case where an account
    has on-demand deposits but no reservation.
    """

    def __init__(self, account_id: str, config: Optional[PaymentConfig] = None):
        self.account_id = account_id
        self.config = config or PaymentConfig()
        self.cumulative_payment = 0

    def set_cumulative_payment(self, amount: int) -> None:
        """Update the cumulative payment amount."""
        self.cumulative_payment = amount

    def account_blob(self, data_len: int) -> tuple[bytes, int]:
        """
        Calculate payment for a blob.

        Args:
            data_len: Length of the encoded blob data

        Returns:
            Tuple of (new_cumulative_payment_bytes, increment)
        """
        # Calculate increment
        increment = calculate_payment_increment(data_len, self.config)

        # Update cumulative payment
        new_payment = self.cumulative_payment + increment

        # Convert to bytes
        payment_bytes = new_payment.to_bytes((new_payment.bit_length() + 7) // 8, "big")

        return payment_bytes, increment


class ReservationAccountant:
    """
    Advanced accountant for handling both reservation and on-demand payments.

    This implementation supports:
    - Per-quorum reservations with period tracking
    - Automatic fallback from reservation to on-demand
    - Thread-safe operations
    - Rollback capability for failed operations
    """

    def __init__(
        self,
        account_id: str,
        reservations: Dict[QuorumID, ReservedPayment],
        quorum_configs: Dict[QuorumID, PaymentQuorumProtocolConfig],
        payment_configs: Dict[QuorumID, PaymentQuorumConfig],
        on_demand_quorums: List[QuorumID],
        payment_config: Optional[PaymentConfig] = None,
    ):
        """
        Initialize the reservation accountant.

        Args:
            account_id: Account identifier
            reservations: Map of quorum ID to reservation
            quorum_configs: Map of quorum ID to protocol config
            payment_configs: Map of quorum ID to payment config
            on_demand_quorums: List of quorums that support on-demand
            payment_config: Configuration for on-demand payments
        """
        self.account_id = account_id
        self.reservations = reservations
        self.quorum_configs = quorum_configs
        self.payment_configs = payment_configs
        self.on_demand_quorums = on_demand_quorums
        self.payment_config = payment_config or PaymentConfig()

        # Period records per quorum
        self.period_records: QuorumPeriodRecords = {}

        # On-demand payment tracking
        self.cumulative_payment = 0

        # Thread safety
        self._lock = threading.Lock()

    def set_cumulative_payment(self, amount: int) -> None:
        """Update the cumulative payment amount."""
        with self._lock:
            self.cumulative_payment = amount

    def account_blob(
        self, data_len: int, quorum_numbers: List[QuorumID], timestamp_ns: int
    ) -> Tuple[bytes, PaymentType, int]:
        """
        Account for a blob using reservation or on-demand payment.

        Args:
            data_len: Length of the encoded blob data
            quorum_numbers: List of quorum IDs
            timestamp_ns: Timestamp in nanoseconds

        Returns:
            Tuple of (payment_bytes, payment_type, increment)
        """
        with self._lock:
            # Try reservation first
            can_use_reservation, reservation_error = self._try_reservation(
                data_len, quorum_numbers, timestamp_ns
            )

            if can_use_reservation:
                return b"", PaymentType.RESERVATION, 0

            # Fall back to on-demand
            return self._try_on_demand(data_len, quorum_numbers)

    def _try_reservation(
        self, data_len: int, quorum_numbers: List[QuorumID], timestamp_ns: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Try to use reservation for payment.

        Returns:
            Tuple of (success, error_message)
        """
        # Calculate symbols needed
        num_symbols = get_blob_length_power_of_2(data_len)

        # Create snapshot for rollback
        snapshot = copy.deepcopy(self.period_records)

        try:
            # Check each quorum
            for quorum_id in quorum_numbers:
                if quorum_id not in self.reservations:
                    return False, f"no reservation for quorum {quorum_id}"

                reservation = self.reservations[quorum_id]
                config = self.quorum_configs.get(quorum_id)

                if not config:
                    return False, f"no protocol config for quorum {quorum_id}"

                # Get or create period records for this quorum
                if quorum_id not in self.period_records:
                    self.period_records[quorum_id] = []

                # Validate and update period
                is_valid, error_msg, period_record = meterer.validate_reservation_period(
                    reservation,
                    self.period_records[quorum_id],
                    timestamp_ns,
                    config.reservation_rate_limit_window,
                    meterer.symbols_charged(num_symbols, config.min_num_symbols),
                )

                if not is_valid:
                    return False, error_msg

                # Update period records
                self.period_records[quorum_id] = meterer.update_period_record(
                    self.period_records[quorum_id],
                    period_record.index,
                    meterer.symbols_charged(num_symbols, config.min_num_symbols),
                )

            return True, None

        except Exception as e:
            # Rollback on error
            self.period_records = snapshot
            return False, str(e)

    def _try_on_demand(
        self, data_len: int, quorum_numbers: List[QuorumID]
    ) -> Tuple[bytes, PaymentType, int]:
        """
        Use on-demand payment.

        Returns:
            Tuple of (payment_bytes, payment_type, increment)
        """
        # Check if all quorums support on-demand
        for quorum_id in quorum_numbers:
            if quorum_id not in self.on_demand_quorums:
                raise ValueError(f"quorum {quorum_id} does not support on-demand payment")

        # Calculate payment increment
        increment = calculate_payment_increment(data_len, self.payment_config)

        # Update cumulative payment
        new_payment = self.cumulative_payment + increment

        # Convert to bytes
        payment_bytes = new_payment.to_bytes((new_payment.bit_length() + 7) // 8, "big")

        # Update state
        self.cumulative_payment = new_payment

        return payment_bytes, PaymentType.ON_DEMAND, increment

    def get_period_records(self, quorum_id: QuorumID) -> List[PeriodRecord]:
        """Get period records for a specific quorum."""
        with self._lock:
            return self.period_records.get(quorum_id, [])
