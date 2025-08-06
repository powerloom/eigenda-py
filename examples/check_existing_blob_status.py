#!/usr/bin/env python3
"""
Example of checking the status of an existing blob.

This example shows how to check the status of a blob using its blob key,
which you might have from a previous dispersal.
"""

import os
import sys

from dotenv import load_dotenv

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2 import DisperserClientV2
from eigenda.core.types import BlobKey, BlobStatus

# Load environment variables
load_dotenv()


def check_existing_blob_status(blob_key_hex: str):
    """
    Check the status of an existing blob.

    Args:
        blob_key_hex: The blob key as a hex string (with or without 0x prefix)
    """
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

    # Create signer
    signer = LocalBlobRequestSigner(private_key)

    # Create client (using basic v2 client, not the Full version)
    client = DisperserClientV2(
        hostname=disperser_host, port=disperser_port, use_secure_grpc=use_secure_grpc, signer=signer
    )

    # Parse blob key
    try:
        blob_key = BlobKey.from_hex(blob_key_hex)
        print(f"Checking status for blob: 0x{blob_key.hex()}")
    except ValueError as e:
        print(f"Invalid blob key: {e}")
        return

    # Check status
    try:
        response = client.get_blob_status(blob_key)

        # Convert protobuf status to our enum
        status = BlobStatus(response.status)

        print(f"\nBlob Status: {status.name} ({status.value})")

        # Provide interpretation
        if status == BlobStatus.UNKNOWN:
            print("⚠️  Status: Unknown - The blob status could not be determined")
            print("   This might mean the blob doesn't exist or there was an error")
        elif status == BlobStatus.QUEUED:
            print("⏳ Status: Queued - The blob is waiting to be processed")
        elif status == BlobStatus.ENCODED:
            print("🔄 Status: Encoded - The blob has been encoded into chunks")
        elif status == BlobStatus.GATHERING_SIGNATURES:
            print("✍️  Status: Gathering Signatures - Collecting signatures from DA nodes")
        elif status == BlobStatus.COMPLETE:
            print("✅ Status: Complete - The blob has been successfully dispersed!")
        elif status == BlobStatus.FAILED:
            print("❌ Status: Failed - The blob dispersal failed")

    except Exception as e:
        print(f"Error checking blob status: {e}")


def main():
    """Main function that handles command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python check_existing_blob_status.py <blob_key_hex>")
        print("\nExample blob keys from previous dispersals:")
        print("  Holesky: 3aaf8a5f848e53a5ecaff30de372a5c0931468d0f46b64fcc5d3984692c0f109")
        print("  Sepolia: 95ae8a8aa08fec0354f439eef31b351da97972916f0bb1c8b4ff8e50a82dc080")
        print("\nExample usage:")
        print(
            "  python check_existing_blob_status.py 3aaf8a5f848e53a5ecaff30de372a5c0931468d0f46b64fcc5d3984692c0f109"
        )
        return

    blob_key_hex = sys.argv[1]
    check_existing_blob_status(blob_key_hex)


if __name__ == "__main__":
    main()
