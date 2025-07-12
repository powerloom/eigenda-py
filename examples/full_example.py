#!/usr/bin/env python3
"""Full example demonstrating blob dispersal and retrieval with EigenDA v2."""

import os
import sys
import time
import traceback
from eigenda.config import get_network_config, get_explorer_url
from eigenda import (
    DisperserClientV2Full,
    BlobRetriever,
    LocalBlobRequestSigner,
    encode_blob_data,
    decode_blob_data,
    BlobStatus
)
from eigenda.payment import PaymentConfig
from dotenv import load_dotenv


def setup_signer():
    """Set up the signer with private key from environment."""
    private_key = os.getenv("EIGENDA_PRIVATE_KEY")
    if not private_key:
        print("Error: EIGENDA_PRIVATE_KEY environment variable not set")
        print("Please set your Ethereum private key in .env file or environment")
        sys.exit(1)

    try:
        signer = LocalBlobRequestSigner(private_key)
        return signer
    except Exception as e:
        print(f"Failed to create signer: {e}")
        sys.exit(1)


def disperse_blob(disperser, original_data):
    """Disperse a blob to EigenDA."""
    raw_data = original_data.encode('utf-8')
    encoded_data = encode_blob_data(raw_data)

    print(f"Original data: {original_data}")
    print(f"Raw size: {len(raw_data)} bytes")
    print(f"Encoded size: {len(encoded_data)} bytes")

    print("\nDispersing blob...")
    status, blob_key = disperser.disperse_blob(
        data=encoded_data,
        blob_version=0,
        quorum_ids=[0, 1]
    )

    print("\n✅ Blob dispersed successfully!")
    print(f"Status: {status.name}")
    print(f"Blob Key: {blob_key.hex()}")
    print(f"Explorer: {get_explorer_url(blob_key.hex())}")

    return status, blob_key


def wait_for_finalization(disperser, blob_key, max_attempts=30):
    """Wait for blob to be finalized on the network."""
    print("\nWaiting for blob to be finalized...")
    attempt = 0

    while attempt < max_attempts:
        time.sleep(2)
        # get_blob_status expects hex string, not BlobKey object
        response = disperser.get_blob_status(blob_key.hex())
        # Parse the status from response
        current_status = BlobStatus(response.status)
        print(f"  Status: {current_status.name}")

        if current_status.name in ["COMPLETE", "GATHERING_SIGNATURES"]:
            print("\n✅ Blob is ready for retrieval!")
            return True
        elif current_status.name == "FAILED":
            print("\n❌ Blob dispersal failed!")
            return False

        attempt += 1

    print("\n⚠️  Timeout waiting for blob finalization")
    print("The blob may still be processing. You can check status later.")
    return False



def main():
    """Run a complete dispersal and retrieval example."""
    print("=== EigenDA V2 Complete Example ===\n")

    # Load environment variables
    load_dotenv()

    # Get network configuration
    network_config = get_network_config()

    # Create signer
    signer = setup_signer()
    print(f"Initialized signer with account: {signer.get_account_id()}")
    print(f"Network: {network_config.network_name}")

    # Step 1: Disperse a blob
    print("\n=== Step 1: Dispersing Blob ===")

    # Create payment config from network config
    payment_config = PaymentConfig(
        price_per_symbol=network_config.price_per_symbol,
        min_num_symbols=network_config.min_num_symbols
    )
    
    disperser = DisperserClientV2Full(
        hostname=network_config.disperser_host,
        port=network_config.disperser_port,
        use_secure_grpc=True,
        signer=signer,
        payment_config=payment_config
    )

    try:
        # Prepare test data
        original_data = (
            f"Hello from Python EigenDA client! "
            f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Disperse the blob
        status, blob_key = disperse_blob(disperser, original_data)

        # Wait for finalization
        finalized = wait_for_finalization(disperser, blob_key)
        if not finalized and status.name == "FAILED":
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Dispersal error: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        disperser.close()

    # Step 2: Retrieve the blob (if available)
    print("\n\n=== Step 2: Blob Retrieval ===")
    print("Note: Blob retrieval requires:")
    print("  1. A retriever service endpoint (not publicly available)")
    print("  2. The full blob header from dispersal (not just the key)")
    print("  3. The reference block number at dispersal time")
    print("  4. The quorum ID to retrieve from")
    print("\nFor a working retrieval example, see:")
    print("  - examples/blob_retrieval_example.py")
    print("  - examples/dispersal_with_retrieval_support.py")
    
    # Example of what retrieval would look like:
    print("\nRetrieval code pattern:")
    print("""
    # retriever = BlobRetriever(hostname="retriever.eigenda.xyz", ...)
    # encoded_data = retriever.retrieve_blob(
    #     blob_header=blob_header,        # Full header from dispersal
    #     reference_block_number=123456,  # Block number at dispersal
    #     quorum_id=0                     # Which quorum to retrieve from
    # )
    # original_data = decode_blob_data(encoded_data)
    """)

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()
