#!/usr/bin/env python3
"""Minimal example of using the EigenDA Python client."""

import os
import sys
import time
from pathlib import Path

# Add the src directory to the path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from eigenda import DisperserClient, LocalBlobRequestSigner
from eigenda.codec import encode_blob_data
from eigenda.config import get_network_config, get_explorer_url


def main():
    """Run a minimal EigenDA client example."""
    print("=== EigenDA V2 Python Client Example ===\n")
    
    # Load environment variables
    load_dotenv()
    
    # Get network configuration
    network_config = get_network_config()
    
    # Get private key from environment
    private_key = os.getenv("EIGENDA_PRIVATE_KEY")
    if not private_key:
        print("Error: EIGENDA_PRIVATE_KEY environment variable not set")
        print("Please set your Ethereum private key in .env file or environment")
        sys.exit(1)
    
    # Create signer
    try:
        signer = LocalBlobRequestSigner(private_key)
        print(f"Initialized signer with account: {signer.get_account_id()}")
        print(f"Network: {network_config.network_name}")
    except Exception as e:
        print(f"Failed to create signer: {e}")
        sys.exit(1)
    
    # Create client
    client = DisperserClient(
        hostname=network_config.disperser_host,
        port=network_config.disperser_port,
        use_secure_grpc=True,
        signer=signer
    )
    
    try:
        # Prepare test data
        test_data = f"Test data from Python client - {time.strftime('%Y-%m-%d %H:%M:%S')}"
        raw_data = test_data.encode('utf-8')
        
        # Encode the data
        encoded_data = encode_blob_data(raw_data)
        
        print(f"\nDispersing {len(raw_data)} bytes (encoded to {len(encoded_data)} bytes)...")
        print(f"Data: {test_data}")
        
        # Disperse the blob
        status, blob_key = client.disperse_blob(
            data=encoded_data,
            blob_version=0,
            quorum_ids=[0, 1]
        )
        
        print(f"\n✅ Success!")
        print(f"Status: {status.name}")
        print(f"Blob Key: {blob_key.hex()}")
        print(f"\nExplorer URL: {get_explorer_url(blob_key.hex())}")
        
        # Check status
        print("\nChecking blob status...")
        final_status = client.get_blob_status(blob_key)
        print(f"Final status: {final_status.name}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        client.close()
        print("\nClient closed.")


if __name__ == "__main__":
    main()