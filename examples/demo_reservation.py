#!/usr/bin/env python3
"""
Demonstrate how reservation-based payment works.

Since we don't have an account with an active reservation,
this shows the expected behavior and payment structure.
"""

import time
from datetime import datetime


def demonstrate_reservation_payment():
    """Show how reservation-based payment works."""

    print("=== Reservation-Based Payment Demo ===\n")

    print("1. RESERVATION STRUCTURE")
    print("-" * 40)
    print("When an account has an active reservation:")
    print("  - symbolsPerSecond: Rate allocated to the account")
    print("  - startTimestamp: When reservation becomes active")
    print("  - endTimestamp: When reservation expires")
    print("  - quorumNumbers: Which quorums can be used")
    print("  - quorumSplits: How bandwidth is split across quorums")

    # Example reservation (what it would look like)
    current_time = int(time.time())
    example_reservation = {
        "symbolsPerSecond": 10000,
        "startTimestamp": current_time - 3600,  # Started 1 hour ago
        "endTimestamp": current_time + 86400 * 29,  # Ends in 29 days
        "quorumNumbers": bytes([0, 1]),  # Can use quorums 0 and 1
        "quorumSplits": bytes([50, 50])  # 50% bandwidth each
    }

    print("\nExample active reservation:")
    print(f"  Symbols/sec: {example_reservation['symbolsPerSecond']}")
    print(f"  Valid from: {datetime.fromtimestamp(example_reservation['startTimestamp'])}")
    print(f"  Valid until: {datetime.fromtimestamp(example_reservation['endTimestamp'])}")
    print(f"  Quorums: {list(example_reservation['quorumNumbers'])}")
    print(f"  Splits: {list(example_reservation['quorumSplits'])}%")

    print("\n2. PAYMENT HEADER FOR RESERVATION")
    print("-" * 40)
    print("For reservation-based payment:")

    # Show payment header structure
    account_id = "0x1234567890123456789012345678901234567890"
    timestamp_ns = int(time.time() * 1e9)

    print(f"  account_id: {account_id}")
    print(f"  timestamp: {timestamp_ns}")
    print("  cumulative_payment: b'' (EMPTY for reservation!)")

    print("\n3. KEY DIFFERENCES")
    print("-" * 40)
    print("Reservation-based:")
    print("  ✓ Pre-paid bandwidth allocation")
    print("  ✓ No per-blob charges")
    print("  ✓ cumulative_payment = empty bytes")
    print("  ✓ Can disperse up to symbolsPerSecond")

    print("\nOn-demand:")
    print("  ✓ Pay per blob")
    print("  ✓ Requires ETH deposit in PaymentVault")
    print("  ✓ cumulative_payment = running total in wei")
    print("  ✓ Each blob increases cumulative payment")

    print("\n4. ACCOUNTANT BEHAVIOR (Go client)")
    print("-" * 40)
    print("The Go client's accountant:")
    print("1. Always tries reservation first")
    print("2. Checks if blob fits within rate limit")
    print("3. If no reservation or exceeds limit → use on-demand")
    print("4. Returns appropriate PaymentMetadata")

    print("\n5. EXAMPLE FLOW")
    print("-" * 40)
    print("Account with 10,000 symbols/sec reservation:")
    print("  - Blob needs 4,096 symbols")
    print("  - Within rate limit → use reservation")
    print("  - PaymentHeader.cumulative_payment = b''")
    print("  - No ETH charged")

    print("\nAccount trying to send too much:")
    print("  - Already used 9,000 symbols this second")
    print("  - New blob needs 4,096 symbols")
    print("  - Exceeds limit → fall back to on-demand")
    print("  - PaymentHeader.cumulative_payment = calculated wei amount")
    print("  - ETH deducted from deposit")


def main():
    demonstrate_reservation_payment()

    print("\n\n💡 TO GET A RESERVATION:")
    print("-" * 40)
    print("1. Visit the EigenDA dashboard")
    print("2. Purchase a reservation plan")
    print("3. Specify bandwidth (symbols/sec)")
    print("4. Select quorums")
    print("5. Pay upfront for the period")
    print("\nOnce active, the Python client will automatically")
    print("detect and use your reservation!")


if __name__ == "__main__":
    main()
