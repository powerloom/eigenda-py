"""Metering utilities for reservation and payment handling."""

import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from eigenda.core.types import PaymentQuorumProtocolConfig, PeriodRecord, QuorumID, ReservedPayment

# Constants from Go implementation
MIN_NUM_BINS = 3  # Fixed number of bins for circular buffer


def within_time(timestamp: datetime, start_timestamp: datetime, end_timestamp: datetime) -> bool:
    """
    Check if a timestamp is within a time range.

    Args:
        timestamp: The timestamp to check
        start_timestamp: Start of the time range
        end_timestamp: End of the time range

    Returns:
        True if timestamp is within range (inclusive), False otherwise
    """
    return start_timestamp <= timestamp <= end_timestamp


def is_reservation_active(reservation: ReservedPayment, current_timestamp: int) -> bool:
    """
    Check if a reservation is active at the given timestamp.

    Args:
        reservation: The reservation to check
        current_timestamp: Current Unix timestamp in seconds

    Returns:
        True if reservation is active, False otherwise
    """
    return reservation.is_active(current_timestamp)


def get_reservation_period_by_nanosecond(timestamp_ns: int, window_seconds: int) -> int:
    """
    Convert nanosecond timestamp to reservation period index.

    Args:
        timestamp_ns: Timestamp in nanoseconds
        window_seconds: Window size in seconds

    Returns:
        Period index (timestamp divided by window)
    """
    timestamp_seconds = timestamp_ns // 1_000_000_000
    return timestamp_seconds // window_seconds


def get_overflow_period(current_period: int, window_seconds: int) -> int:
    """
    Get the overflow period (current + 2*window).

    Args:
        current_period: Current period index
        window_seconds: Window size in seconds

    Returns:
        Overflow period index
    """
    return current_period + 2 * window_seconds


def get_bin_index(period: int, num_bins: int = MIN_NUM_BINS) -> int:
    """
    Get the bin index for a given period using modular arithmetic.

    Args:
        period: Period index
        num_bins: Number of bins (default: MIN_NUM_BINS)

    Returns:
        Bin index (0 to num_bins-1)
    """
    return period % num_bins


def symbols_charged(num_symbols: int, min_num_symbols: int) -> int:
    """
    Calculate the number of symbols charged, respecting minimum.

    Args:
        num_symbols: Actual number of symbols
        min_num_symbols: Minimum number of symbols to charge

    Returns:
        Number of symbols to charge (max of actual and minimum)
    """
    return max(num_symbols, min_num_symbols)


def payment_charged(num_symbols: int, price_per_symbol: int) -> int:
    """
    Calculate payment in wei for given number of symbols.

    Args:
        num_symbols: Number of symbols
        price_per_symbol: Price per symbol in wei

    Returns:
        Total payment in wei
    """
    return num_symbols * price_per_symbol


def nanoseconds_to_seconds(timestamp_ns: int) -> int:
    """
    Convert nanoseconds to seconds.

    Args:
        timestamp_ns: Timestamp in nanoseconds

    Returns:
        Timestamp in seconds
    """
    return timestamp_ns // 1_000_000_000


def seconds_to_nanoseconds(timestamp_s: int) -> int:
    """
    Convert seconds to nanoseconds.

    Args:
        timestamp_s: Timestamp in seconds

    Returns:
        Timestamp in nanoseconds
    """
    return timestamp_s * 1_000_000_000


def current_time_nanoseconds() -> int:
    """
    Get current time in nanoseconds.

    Returns:
        Current timestamp in nanoseconds
    """
    return int(time.time() * 1_000_000_000)


def validate_timestamp_range(
    timestamp_ns: int, start_timestamp_s: int, end_timestamp_s: int
) -> Tuple[bool, str]:
    """
    Validate if a nanosecond timestamp is within a second-based range.

    Args:
        timestamp_ns: Timestamp to check in nanoseconds
        start_timestamp_s: Start timestamp in seconds
        end_timestamp_s: End timestamp in seconds

    Returns:
        Tuple of (is_valid, error_message)
    """
    timestamp_s = nanoseconds_to_seconds(timestamp_ns)

    if timestamp_s < start_timestamp_s:
        return False, f"timestamp {timestamp_s} is before reservation start {start_timestamp_s}"

    if timestamp_s > end_timestamp_s:
        return False, f"timestamp {timestamp_s} is after reservation end {end_timestamp_s}"

    return True, ""


def get_reservation_bin_limit(
    symbols_per_second: int, window_seconds: int, num_bins: int = MIN_NUM_BINS
) -> int:
    """
    Calculate the bin limit for a reservation.

    Args:
        symbols_per_second: Reservation rate
        window_seconds: Window size in seconds
        num_bins: Number of bins

    Returns:
        Maximum symbols per bin
    """
    return symbols_per_second * window_seconds * num_bins


def is_within_advance_window(
    current_timestamp_s: int, reservation_start_s: int, advance_window_s: int
) -> bool:
    """
    Check if current time is within the advance window before reservation starts.

    Args:
        current_timestamp_s: Current timestamp in seconds
        reservation_start_s: Reservation start timestamp in seconds
        advance_window_s: Advance window size in seconds

    Returns:
        True if within advance window, False otherwise
    """
    if current_timestamp_s >= reservation_start_s:
        return True  # Already active

    earliest_allowed = reservation_start_s - advance_window_s
    return current_timestamp_s >= earliest_allowed


# Reservation Validation Functions
def validate_reservations(
    reservations: Dict[QuorumID, ReservedPayment],
    quorum_configs: Dict[QuorumID, PaymentQuorumProtocolConfig],
    quorum_numbers: List[QuorumID],
    payment_header_timestamp_ns: int,
    received_timestamp_ns: int,
) -> Optional[str]:
    """
    Validate reservations for the requested quorums.

    Args:
        reservations: Map of quorum ID to reservation
        quorum_configs: Map of quorum ID to protocol config
        quorum_numbers: List of requested quorum IDs
        payment_header_timestamp_ns: Timestamp from payment header in nanoseconds
        received_timestamp_ns: Timestamp when request was received in nanoseconds

    Returns:
        Error message if validation fails, None if successful
    """
    # Check if all requested quorums have reservations
    for quorum_id in quorum_numbers:
        if quorum_id not in reservations:
            return f"no reservation for quorum {quorum_id}"

    # Validate each reservation
    for quorum_id in quorum_numbers:
        reservation = reservations[quorum_id]
        config = quorum_configs.get(quorum_id)

        if not config:
            return f"no protocol config for quorum {quorum_id}"

        # Validate reservation is active
        current_time_s = nanoseconds_to_seconds(received_timestamp_ns)
        if not reservation.is_active(current_time_s):
            return f"reservation for quorum {quorum_id} is not active at {current_time_s}"

        # Validate timestamp is within reservation range
        is_valid, error_msg = validate_timestamp_range(
            payment_header_timestamp_ns, reservation.start_timestamp, reservation.end_timestamp
        )
        if not is_valid:
            return f"quorum {quorum_id}: {error_msg}"

        # Check if within advance window
        if not is_within_advance_window(
            current_time_s, reservation.start_timestamp, config.reservation_advance_window
        ):
            return (
                f"reservation for quorum {quorum_id} starts at {reservation.start_timestamp}, "
                f"current time {current_time_s} is not within advance window"
            )

    return None


def validate_reservation_period(
    reservation: ReservedPayment,
    period_records: List[PeriodRecord],
    timestamp_ns: int,
    window_seconds: int,
    symbols_to_charge: int,
) -> Tuple[bool, str, Optional[PeriodRecord]]:
    """
    Validate if reservation has capacity for the requested symbols.

    Args:
        reservation: The reservation to validate
        period_records: Period records for the reservation
        timestamp_ns: Request timestamp in nanoseconds
        window_seconds: Window size in seconds
        symbols_to_charge: Number of symbols to charge

    Returns:
        Tuple of (is_valid, error_message, period_record)
    """
    # Get current period
    current_period = get_reservation_period_by_nanosecond(timestamp_ns, window_seconds)
    bin_index = get_bin_index(current_period)

    # Find or create period record
    period_record = None
    for record in period_records:
        if get_bin_index(record.index) == bin_index:
            period_record = record
            break

    if not period_record:
        # Create new period record
        period_record = PeriodRecord(index=current_period, usage=0)

    # Check if period matches current or allows overflow
    if period_record.index != current_period:
        # Check if this is a valid overflow from previous period
        if period_record.index > current_period:
            return False, f"period {current_period} is in the past", None

    # Calculate bin limit
    bin_limit = get_reservation_bin_limit(
        reservation.symbols_per_second, window_seconds, MIN_NUM_BINS
    )

    # Check capacity
    if period_record.usage + symbols_to_charge > bin_limit:
        return (
            False,
            (
                f"insufficient reservation capacity: need {symbols_to_charge} symbols, "
                f"bin has {period_record.usage}/{bin_limit} used"
            ),
            None,
        )

    return True, "", period_record


def check_quorum_in_reservation(reservation: ReservedPayment, quorum_id: QuorumID) -> bool:
    """
    Check if a quorum is included in the reservation.

    Args:
        reservation: The reservation to check
        quorum_id: The quorum ID to look for

    Returns:
        True if quorum is in reservation, False otherwise
    """
    return quorum_id in reservation.quorum_numbers


def validate_payment_increment(
    current_payment: int, new_payment: int, min_increment: int
) -> Tuple[bool, str]:
    """
    Validate that payment increment is sufficient.

    Args:
        current_payment: Current cumulative payment
        new_payment: New cumulative payment
        min_increment: Minimum required increment

    Returns:
        Tuple of (is_valid, error_message)
    """
    increment = new_payment - current_payment

    if increment < min_increment:
        return False, (
            f"insufficient payment increment: got {increment}, " f"required minimum {min_increment}"
        )

    return True, ""


def update_period_record(
    period_records: List[PeriodRecord],
    period: int,
    symbols_to_add: int,
    max_bins: int = MIN_NUM_BINS,
) -> List[PeriodRecord]:
    """
    Update period records with new usage.

    Args:
        period_records: Current period records
        period: Period index to update
        symbols_to_add: Number of symbols to add
        max_bins: Maximum number of bins

    Returns:
        Updated period records
    """
    bin_index = get_bin_index(period, max_bins)

    # Find existing record
    for record in period_records:
        if get_bin_index(record.index, max_bins) == bin_index:
            record.usage += symbols_to_add
            record.index = period  # Update to current period
            return period_records

    # Create new record if not found
    new_record = PeriodRecord(index=period, usage=symbols_to_add)

    # Keep only the most recent records (up to max_bins)
    period_records.append(new_record)
    if len(period_records) > max_bins:
        # Remove oldest records
        period_records.sort(key=lambda r: r.index, reverse=True)
        period_records = period_records[:max_bins]

    return period_records
