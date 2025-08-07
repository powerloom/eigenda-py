#!/usr/bin/env python3
"""Test both reservation-based and on-demand payment methods."""

import os
from datetime import datetime

from dotenv import load_dotenv
from eth_account import Account

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.config import get_explorer_url, get_network_config
from eigenda.payment import PaymentConfig


def test_account(private_key: str, description: str):
    """Test an account to see what payment method it uses."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print("=" * 60)

    # Get network configuration
    network_config = get_network_config()

    # Initialize signer
    signer = LocalBlobRequestSigner(private_key)
    print(f"Account: {signer.account}")
    print(f"Network: {network_config.network_name}")

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
        # Check payment configuration
        print("\nChecking payment configuration...")

        # Get payment info
        payment_info = client.get_payment_info()
        print(f"Payment type: {payment_info['payment_type']}")
        print(f"Has reservation: {payment_info['has_reservation']}")

        if payment_info["payment_type"] == "reservation" and payment_info["reservation_details"]:
            details = payment_info["reservation_details"]
            print(f"Symbols per second: {details['symbols_per_second']}")
            print(f"Time remaining: {details['time_remaining']} seconds")
            print(f"Allowed quorums: {details['quorum_numbers']}")
            print(f"Quorum splits: {details['quorum_splits']}%")
        elif payment_info["payment_type"] == "on_demand":
            print(f"Current cumulative payment: {payment_info['current_cumulative_payment']} wei")
            balance_wei = payment_info["onchain_balance"]
            balance_eth = balance_wei / 1e18
            print(f"Onchain balance: {balance_wei} wei ({balance_eth:.4f} ETH)")
            print(f"Price per symbol: {payment_info['price_per_symbol']} wei")
            print(f"Min symbols: {payment_info['min_symbols']}")

        # Try to disperse a blob
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_data = f"Test {payment_info['payment_type']} - {timestamp}".encode()
        print(f"\nTest data: {test_data.decode()}")
        print(f"Data size: {len(test_data)} bytes")

        # Disperse blob (DisperserClientV2Full handles encoding internally)
        status, blob_key = client.disperse_blob(
            data=test_data, blob_version=0, quorum_numbers=[0, 1]
        )

        print("\n✅ Success!")
        print(f"Status: {status}")
        print(f"Blob Key: {blob_key.hex()}")
        print(f"Explorer: {get_explorer_url(blob_key.hex())}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        client.close()


def main():
    print("=== EigenDA V2 - Test Both Payment Methods ===")

    # Load environment variables
    load_dotenv()

    # Test with the main account (has on-demand deposit)
    main_key = os.environ.get("EIGENDA_PRIVATE_KEY")
    if main_key:
        test_account(main_key, "Main account (with on-demand deposit)")

    # Test with a different account if available
    # You can set EIGENDA_PRIVATE_KEY_2 in .env for an account with reservation
    alt_key = os.environ.get("EIGENDA_PRIVATE_KEY_2")
    if alt_key:
        test_account(alt_key, "Alternative account (might have reservation)")
    else:
        print("\n💡 Tip: Set EIGENDA_PRIVATE_KEY_2 in .env to test an account with reservation")

        # Generate a new test account to show what happens with no payment
        print("\nGenerating a new account with no deposits or reservations...")
        new_account = Account.create()
        print(f"New account: {new_account.address}")
        print("(This account has no ETH deposits or reservations)")

        # Test it
        test_account(new_account.key.hex(), "New account (no payment methods)")


if __name__ == "__main__":
    main()
