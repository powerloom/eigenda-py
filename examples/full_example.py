#!/usr/bin/env python3
"""Full example demonstrating blob dispersal and retrieval with EigenDA v2."""

import os
import sys
import time
from pathlib import Path

# Add the src directory to the path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from eigenda import (
    DisperserClientV2, 
    BlobRetriever,
    LocalBlobRequestSigner,
    encode_blob_data,
    decode_blob_data
)
from eigenda.config import get_network_config, get_explorer_url


def main():
    """Run a complete dispersal and retrieval example."""
    print("=== EigenDA V2 Complete Example ===\n")
    
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
    
    # Step 1: Disperse a blob
    print("\n=== Step 1: Dispersing Blob ===")
    
    disperser = DisperserClientV2(
        hostname=network_config.disperser_host,
        port=network_config.disperser_port,
        use_secure_grpc=True,
        signer=signer
    )
    
    try:
        # Prepare test data
        original_data = f"Hello from Python EigenDA client! Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        raw_data = original_data.encode('utf-8')
        
        # Encode the data
        encoded_data = encode_blob_data(raw_data)
        
        print(f"Original data: {original_data}")
        print(f"Raw size: {len(raw_data)} bytes")
        print(f"Encoded size: {len(encoded_data)} bytes")
        
        # Disperse the blob
        print("\nDispersing blob...")
        status, blob_key = disperser.disperse_blob(
            data=encoded_data,
            blob_version=0,
            quorum_ids=[0, 1]
        )
        
        print(f"\n✅ Blob dispersed successfully!")
        print(f"Status: {status.name}")
        print(f"Blob Key: {blob_key.hex()}")
        print(f"Explorer: {get_explorer_url(blob_key.hex())}")
        
        # Wait for blob to be finalized
        print("\nWaiting for blob to be finalized...")
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(2)
            current_status = disperser.get_blob_status(blob_key)
            print(f"  Status: {current_status.name}")
            
            if current_status.name in ["COMPLETE", "GATHERING_SIGNATURES"]:
                print(f"\n✅ Blob is ready for retrieval!")
                break
            elif current_status.name == "FAILED":
                print(f"\n❌ Blob dispersal failed!")
                sys.exit(1)
            
            attempt += 1
        
        if attempt >= max_attempts:
            print(f"\n⚠️  Timeout waiting for blob finalization")
            print("The blob may still be processing. You can check status later.")
        
    except Exception as e:
        print(f"\n❌ Dispersal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        disperser.close()
    
    # Step 2: Retrieve the blob (if available)
    print("\n\n=== Step 2: Retrieving Blob ===")
    print("Note: Retrieval requires a retriever endpoint which may not be publicly available")
    print("This is shown for demonstration purposes")
    
    # Example retriever configuration (may not be accessible)
    # Note: retriever endpoints may differ from disperser endpoints
    retriever_host = network_config.disperser_host.replace("disperser", "retriever")
    retriever = BlobRetriever(
        hostname=retriever_host,  # Example endpoint
        port=443,
        use_secure_grpc=True,
        signer=signer
    )
    
    try:
        print(f"\nAttempting to retrieve blob: {blob_key.hex()}")
        
        # Get blob info first
        try:
            blob_size, encoding_version = retriever.get_blob_info(blob_key)
            print(f"Blob size: {blob_size} bytes")
            print(f"Encoding version: {encoding_version}")
        except Exception as e:
            print(f"Could not get blob info: {e}")
        
        # Retrieve the blob
        retrieved_data = retriever.retrieve_blob(blob_key)
        print(f"\n✅ Blob retrieved successfully!")
        print(f"Retrieved size: {len(retrieved_data)} bytes")
        
        # Decode the data
        decoded_data = decode_blob_data(retrieved_data)
        retrieved_text = decoded_data.decode('utf-8')
        
        print(f"\nDecoded data: {retrieved_text}")
        
        # Verify it matches
        if retrieved_text == original_data:
            print("\n✅ Data integrity verified - retrieved data matches original!")
        else:
            print("\n❌ Data mismatch - retrieved data differs from original!")
            
    except Exception as e:
        print(f"\n⚠️  Retrieval error (this is expected if retriever is not available): {e}")
        print("\nNote: Blob retrieval typically requires:")
        print("  1. Access to a retriever service endpoint")
        print("  2. The blob to be fully finalized on the network")
        print("  3. Proper authentication/authorization")
    finally:
        retriever.close()
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()