#!/usr/bin/env python3
"""
Example of checking blob status after dispersal.

This example shows how to:
1. Disperse a blob to EigenDA
2. Check the blob status repeatedly until it reaches a terminal state
3. Handle different status values correctly
"""

import os
import time

from dotenv import load_dotenv

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.core.types import BlobStatus

# Load environment variables
load_dotenv()


def check_blob_status_example():
    """Example of dispersing a blob and checking its status."""
    # Get configuration from environment
    private_key = os.getenv("EIGENDA_PRIVATE_KEY")
    if not private_key:
        print("Error: EIGENDA_PRIVATE_KEY environment variable not set")
        print("Please set it to your Ethereum private key (with 0x prefix)")
        return

    disperser_host = os.getenv("EIGENDA_DISPERSER_HOST", "disperser-testnet-sepolia.eigenda.xyz")
    disperser_port = int(os.getenv("EIGENDA_DISPERSER_PORT", "443"))
    use_secure_grpc = os.getenv("EIGENDA_USE_SECURE_GRPC", "true").lower() == "true"

    print(f"Connecting to disperser at {disperser_host}:{disperser_port}")
    print(f"Using secure gRPC: {use_secure_grpc}")

    # Create signer
    signer = LocalBlobRequestSigner(private_key)
    account = signer.get_account_id()
    print(f"Using account: {account}")

    # Create client
    client = DisperserClientV2Full(
        hostname=disperser_host, port=disperser_port, use_secure_grpc=use_secure_grpc, signer=signer
    )

    # Data to disperse
    raw_data = b"Hello, EigenDA! This is a test blob for status checking."

    # Disperse the blob (DisperserClientV2Full handles encoding internally)
    print(f"\nDispersing blob ({len(raw_data)} bytes)...")
    try:
        status, blob_key = client.disperse_blob(
            data=raw_data, blob_version=0, quorum_numbers=[0, 1]  # Use quorums 0 and 1
        )

        print(f"Initial status: {status.name} ({status.value})")
        print(f"Blob key: 0x{blob_key.hex()}")

    except Exception as e:
        print(f"Error dispersing blob: {e}")
        return

    # Check status until it reaches a terminal state
    print("\nChecking blob status...")

    # Terminal states that indicate we should stop polling
    terminal_states = {BlobStatus.COMPLETE, BlobStatus.FAILED, BlobStatus.UNKNOWN}

    # Maximum number of attempts
    max_attempts = 30
    attempt = 0

    while attempt < max_attempts:
        try:
            # Wait a bit before checking
            time.sleep(2)

            # Get current status (pass hex string, not BlobKey object)
            response = client.get_blob_status(blob_key.hex())

            # Parse the status from the response
            current_status = BlobStatus(response.status)

            print(f"Attempt {attempt + 1}: Status = {current_status.name} ({current_status.value})")

            # Check if we've reached a terminal state
            if current_status in terminal_states:
                print(f"\nBlob reached terminal state: {current_status.name}")

                if current_status == BlobStatus.COMPLETE:
                    print("✅ Blob successfully dispersed and confirmed!")
                elif current_status == BlobStatus.FAILED:
                    print("❌ Blob dispersal failed")
                else:  # UNKNOWN
                    print("⚠️  Blob status is unknown (this might indicate an error)")

                break

            # Show progress for intermediate states
            if current_status == BlobStatus.QUEUED:
                print("   → Blob is queued for processing")
            elif current_status == BlobStatus.ENCODED:
                print("   → Blob has been encoded")
            elif current_status == BlobStatus.GATHERING_SIGNATURES:
                print("   → Gathering signatures from nodes")

            attempt += 1

        except Exception as e:
            print(f"Error checking status: {e}")
            attempt += 1
            continue

    if attempt >= max_attempts:
        print(f"\n⏱️  Timeout: Blob did not reach terminal state after {max_attempts} attempts")
        print("The blob might still be processing. You can check again later with the blob key.")

    # Print summary
    print("\n" + "=" * 50)
    print("BLOB STATUS REFERENCE:")
    print("=" * 50)
    print("The v2 protocol uses these status values:")
    print(f"  {BlobStatus.UNKNOWN.value}: {BlobStatus.UNKNOWN.name} - Error or unknown state")
    print(f"  {BlobStatus.QUEUED.value}: {BlobStatus.QUEUED.name} - Blob queued for processing")
    print(f"  {BlobStatus.ENCODED.value}: {BlobStatus.ENCODED.name} - Blob encoded into chunks")
    print(
        f"  {BlobStatus.GATHERING_SIGNATURES.value}: {BlobStatus.GATHERING_SIGNATURES.name} - Collecting node signatures"
    )
    print(f"  {BlobStatus.COMPLETE.value}: {BlobStatus.COMPLETE.name} - Successfully dispersed")
    print(f"  {BlobStatus.FAILED.value}: {BlobStatus.FAILED.name} - Dispersal failed")


if __name__ == "__main__":
    check_blob_status_example()
