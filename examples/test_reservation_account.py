#!/usr/bin/env python3
"""
Check if account has an active reservation.

This example demonstrates:
1. Detecting if an account has an active reservation
2. Showing reservation details (bandwidth, expiry, quorums)
3. Dispersing a blob using reservation (no ETH charges)
4. Verifying no payment is charged when using reservation
"""

import os
import time
from datetime import datetime

from dotenv import load_dotenv

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.config import get_explorer_url, get_network_config
from eigenda.core.types import BlobStatus
from eigenda.payment import PaymentConfig


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        return f"{seconds//60} minutes, {seconds % 60} seconds"
    elif seconds < 86400:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours} hours, {mins} minutes"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days} days, {hours} hours"


def test_reservation_account():
    """Check if account has an active reservation."""

    print("=== EigenDA Reservation Check ===\n")

    # Load environment variables
    load_dotenv()

    # Get network configuration
    network_config = get_network_config()
    print(f"Network: {network_config.network_name}")
    print(f"Disperser: {network_config.disperser_host}")

    # Get private key from environment
    private_key = os.getenv("EIGENDA_PRIVATE_KEY")

    if not private_key:
        print("\nError: EIGENDA_PRIVATE_KEY environment variable not set")
        print("Please set it to your Ethereum private key (with 0x prefix)")
        return

    # Initialize signer
    signer = LocalBlobRequestSigner(private_key)
    account_address = signer.get_account_id()
    print(f"Account address: {account_address}")

    # Create client with full payment support
    client = DisperserClientV2Full(
        hostname=network_config.disperser_host,
        port=network_config.disperser_port,
        use_secure_grpc=True,
        signer=signer,
        payment_config=PaymentConfig(
            price_per_symbol=network_config.price_per_symbol,
            min_num_symbols=network_config.min_num_symbols,
        ),
    )

    try:
        print("\n" + "=" * 60)
        print("CHECKING PAYMENT STATE")
        print("=" * 60)

        # Get detailed payment information
        payment_info = client.get_payment_info()

        if payment_info["payment_type"] == "reservation":
            print("\n✅ RESERVATION DETECTED!")

            if payment_info["reservation_details"]:
                details = payment_info["reservation_details"]

                print("\nReservation Details:")
                print(f"  • Bandwidth: {details['symbols_per_second']:,} symbols/second")
                start_str = datetime.fromtimestamp(details["start_timestamp"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                print(f"  • Started: {start_str}")
                end_str = datetime.fromtimestamp(details["end_timestamp"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                print(f"  • Expires: {end_str}")
                print(f"  • Time remaining: {format_duration(details['time_remaining'])}")
                print(f"  • Allowed quorums: {details['quorum_numbers']}")
                print(f"  • Quorum bandwidth splits: {details['quorum_splits']}%")

                # Calculate daily/monthly capacity
                daily_capacity = details["symbols_per_second"] * 86400
                monthly_capacity = details["symbols_per_second"] * 86400 * 30
                print("\nCapacity:")
                print(f"  • Per second: {details['symbols_per_second']:,} symbols")
                daily_mb = daily_capacity * 31 / (1024 * 1024)
                print(f"  • Per day: {daily_capacity:,} symbols (~{daily_mb:.2f} MB)")
                monthly_mb = monthly_capacity * 31 / (1024 * 1024)
                print(f"  • Per month: {monthly_capacity:,} symbols (~{monthly_mb:.2f} MB)")

                print("\n" + "=" * 60)
                print("TESTING BLOB DISPERSAL WITH RESERVATION")
                print("=" * 60)

                # Record initial payment state
                initial_cumulative = payment_info["current_cumulative_payment"]
                print(f"\nInitial cumulative payment: {initial_cumulative} wei")

                # Create test data
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                test_data = f"Reservation test at {timestamp}".encode()

                print(f"\nTest data: '{test_data.decode()}'")
                print(f"Data size: {len(test_data)} bytes")

                # Disperse blob
                print("Dispersing blob...", end="")
                start_time = time.time()

                status, blob_key = client.disperse_blob(
                    data=test_data,
                    blob_version=0,
                    quorum_numbers=(
                        details["quorum_numbers"][:2]
                        if len(details["quorum_numbers"]) >= 2
                        else [0]
                    ),
                )

                elapsed = time.time() - start_time
                print(f" Done in {elapsed:.2f}s")

                print("\n✅ Blob dispersed successfully!")
                print(f"  Status: {status.name}")
                print(f"  Blob key: {blob_key.hex()}")
                print(f"  Explorer URL: {get_explorer_url(blob_key.hex())}")

                # Verify no charges
                print("\n" + "=" * 60)
                print("VERIFYING NO CHARGES")
                print("=" * 60)

                # Get updated payment info
                final_payment_info = client.get_payment_info()
                final_cumulative = final_payment_info["current_cumulative_payment"]

                print(f"\nInitial cumulative payment: {initial_cumulative} wei")
                print(f"Final cumulative payment: {final_cumulative} wei")
                print(f"Payment charged: {final_cumulative - initial_cumulative} wei")

                if final_cumulative == initial_cumulative:
                    print("\n✅ SUCCESS: No payment charged (using reservation)")
                else:
                    increase = final_cumulative - initial_cumulative
                    print(f"\n⚠️  WARNING: Payment increased by {increase} wei")

        else:
            print("\n❌ NO ACTIVE RESERVATION FOUND")

            if payment_info["payment_type"] == "on_demand":
                print("\nThis account is using on-demand payment instead.")
                balance_wei = payment_info["onchain_balance"]
                balance_eth = balance_wei / 1e18
                print(f"Current balance: {balance_wei} wei ({balance_eth:.4f} ETH)")
            else:
                print("\nThis account has no payment method configured.")

            print("\nTo get a reservation:")
            print("  1. Visit the EigenDA dashboard")
            print("  2. Purchase a reservation plan")
            print("  3. Specify bandwidth (symbols/sec)")
            print("  4. Select quorums")
            print("  5. Pay upfront for the period")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        client.close()
        print("\n✓ Client closed")


def main():
    """Main entry point."""
    test_reservation_account()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("\nReservations provide:")
    print("  • Pre-paid bandwidth allocation")
    print("  • No per-blob charges")
    print("  • Guaranteed throughput")
    print("  • Predictable costs")
    print("\nThe Python client automatically detects and uses")
    print("reservations when available!")


if __name__ == "__main__":
    main()
