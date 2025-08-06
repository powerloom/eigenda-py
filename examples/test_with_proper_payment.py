#!/usr/bin/env python3
"""Test with properly calculated on-demand payment."""

import os
import time
import traceback
from datetime import datetime

from dotenv import load_dotenv

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2 import DisperserClientV2
from eigenda.codec.blob_codec import encode_blob_data
from eigenda.config import get_explorer_url, get_network_config
from eigenda.grpc.common.v2 import common_v2_pb2

# Constants from the PaymentVault contract (will be set in main)
PRICE_PER_SYMBOL = None
MIN_NUM_SYMBOLS = None


def get_blob_length_power_of_2(data_len: int) -> int:
    """
    Calculate the number of symbols for a blob, rounding up to power of 2.
    This matches the Go implementation in encoding/utils.go
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


def calculate_payment_increment(data_len: int) -> int:
    """Calculate the payment increment for a blob of given size."""
    # Get number of symbols (power of 2)
    num_symbols = get_blob_length_power_of_2(data_len)

    # Ensure minimum symbols
    if num_symbols < MIN_NUM_SYMBOLS:
        num_symbols = MIN_NUM_SYMBOLS

    # Calculate payment
    payment = num_symbols * PRICE_PER_SYMBOL

    print(f"  Data length: {data_len} bytes")
    print(f"  Symbols: {num_symbols}")
    print(f"  Payment: {payment} wei ({payment / 1e9:.3f} gwei)")

    return payment


def main():
    print("=== EigenDA V2 Test with Proper Payment ===\n")

    # Load environment variables
    load_dotenv()

    # Get network configuration
    network_config = get_network_config()

    # Set constants from network config
    global PRICE_PER_SYMBOL, MIN_NUM_SYMBOLS
    PRICE_PER_SYMBOL = network_config.price_per_symbol
    MIN_NUM_SYMBOLS = network_config.min_num_symbols

    # Get private key
    private_key = os.environ.get("EIGENDA_PRIVATE_KEY")
    if not private_key:
        print("Error: EIGENDA_PRIVATE_KEY environment variable not set")
        return

    # Initialize signer
    signer = LocalBlobRequestSigner(private_key)
    print(f"Account: {signer.account.address}")
    print(f"Network: {network_config.network_name}\n")

    # Create client using network configuration
    client = DisperserClientV2(
        hostname=network_config.disperser_host,
        port=network_config.disperser_port,
        use_secure_grpc=True,
        signer=signer,
    )

    try:
        # Get payment state
        print("Getting payment state...")
        payment_state = client.get_payment_state()

        # Check for on-demand payment existence
        if (
            not hasattr(payment_state, "onchain_cumulative_payment")
            or not payment_state.onchain_cumulative_payment
        ):
            print("\n❌ Error: No on-demand payment deposit found for this account.")
            print("Please deposit funds into the PaymentVault contract for on-demand payments.")
            print(f"  - Network: {network_config.network_name}")
            print(f"  - PaymentVault: {network_config.payment_vault_address}")
            return

        print("✅ Payment state retrieved")

        # Get current cumulative payment
        current_payment = int.from_bytes(payment_state.cumulative_payment, "big")
        print(f"Current cumulative payment: {current_payment} wei")

        # Prepare test data
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_data = f"Test {timestamp}".encode()
        print("\nPreparing blob:")
        print(f"  Raw data: {len(test_data)} bytes")

        # Encode data
        encoded_data = encode_blob_data(test_data)
        print(f"  Encoded: {len(encoded_data)} bytes")

        # Calculate payment increment
        print("\nCalculating payment:")
        increment = calculate_payment_increment(len(encoded_data))
        new_payment = current_payment + increment
        new_payment_bytes = new_payment.to_bytes((new_payment.bit_length() + 7) // 8, "big")

        print("\nPayment summary:")
        print(f"  Current: {current_payment} wei")
        print(f"  Increment: {increment} wei")
        print(f"  New total: {new_payment} wei")

        # Override the _create_blob_header method
        client._create_blob_header

        def custom_create_header(blob_version, blob_commitment, quorum_numbers):
            account_id = signer.get_account_id()
            timestamp_ns = int(time.time() * 1e9)

            # Use our calculated payment
            payment_header = common_v2_pb2.PaymentHeader(
                account_id=account_id, timestamp=timestamp_ns, cumulative_payment=new_payment_bytes
            )

            blob_header = common_v2_pb2.BlobHeader(
                version=blob_version,
                commitment=blob_commitment,
                quorum_numbers=quorum_numbers,
                payment_header=payment_header,
            )

            return blob_header

        # Monkey patch for this test
        client._create_blob_header = custom_create_header

        # Disperse blob
        print("\nDispersing blob...")
        status, blob_key = client.disperse_blob(
            data=encoded_data, blob_version=0, quorum_ids=[0, 1]
        )

        print("\n✅ Success!")
        print(f"Status: {status}")
        print(f"Blob Key: {blob_key.hex()}")
        print(f"\nExplorer: {get_explorer_url(blob_key.hex())}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
    finally:
        client.close()
        print("\nClient closed.")


if __name__ == "__main__":
    main()
