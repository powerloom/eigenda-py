"""Payment calculation utilities for EigenDA on-demand payments."""

from dataclasses import dataclass
from typing import Optional


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
        self.cumulative_payment = new_payment  # Update internal state

        # Convert to bytes
        payment_bytes = new_payment.to_bytes((new_payment.bit_length() + 7) // 8, "big")

        return payment_bytes, increment
