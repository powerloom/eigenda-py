"""
Example showing how to modify the dispersal process to support later retrieval.

The key insight is that we need to save the blob header from dispersal
to be able to retrieve the blob later.
"""

import json
import os
import time
from typing import Any, Tuple

from dotenv import load_dotenv

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.config import get_network_config
from eigenda.core.types import BlobKey, BlobStatus
from eigenda.payment import PaymentConfig

# Load environment variables
load_dotenv()


class DisperserWithRetrieval(DisperserClientV2Full):
    """
    Extended disperser client that returns blob header for retrieval.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_blob_header = None
        self._last_reference_block = None

    def disperse_blob_with_header(
        self, data: bytes, blob_version: int = 0, quorum_numbers: list = None
    ) -> Tuple[BlobStatus, BlobKey, Any, int]:
        """
        Disperse a blob and return the header needed for retrieval.

        Returns:
            Tuple of (status, blob_key, blob_header, reference_block)
        """
        # Store the original disperse_blob method
        original_create_header = self._create_blob_header
        blob_header_capture = None

        # Wrap _create_blob_header to capture the header
        def capture_header(*args, **kwargs):
            nonlocal blob_header_capture
            blob_header_capture = original_create_header(*args, **kwargs)
            return blob_header_capture

        # Temporarily replace the method
        self._create_blob_header = capture_header

        try:
            # Get current Ethereum block (in practice, you'd query an Ethereum node)
            # For demo purposes, we'll use a mock block number
            reference_block = int(time.time() // 12)  # Rough approximation

            # Disperse the blob
            status, blob_key = self.disperse_blob(data, quorum_numbers, blob_version)

            # Return status, key, header, and block number
            return status, blob_key, blob_header_capture, reference_block

        finally:
            # Restore original method
            self._create_blob_header = original_create_header


def save_blob_metadata(
    blob_key: BlobKey, blob_header: Any, reference_block: int, quorum_id: int = 0
):
    """Save blob metadata for later retrieval."""
    metadata = {
        "blob_key": blob_key.hex(),
        "reference_block": reference_block,
        "quorum_id": quorum_id,
        "timestamp": int(time.time()),
        # Note: blob_header is a protobuf object, would need serialization in practice
        "blob_header_info": {
            "version": blob_header.version if hasattr(blob_header, "version") else 0,
            "quorum_numbers": (
                list(blob_header.quorum_numbers) if hasattr(blob_header, "quorum_numbers") else [0]
            ),
        },
    }

    # Save to file (in practice, use a database)
    filename = f"blob_metadata_{blob_key.hex()[:8]}.json"
    with open(filename, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved blob metadata to {filename}")
    return filename


def main():
    """Demonstrate dispersal with retrieval support."""

    # Check for private key
    private_key = os.getenv("EIGENDA_PRIVATE_KEY")
    if not private_key:
        print("Error: EIGENDA_PRIVATE_KEY environment variable not set")
        return

    # Initialize components
    signer = LocalBlobRequestSigner(private_key)
    network_config = get_network_config()

    print(f"Using network: {network_config.network_name}")
    print(f"Account: {signer.get_account_id()}")
    print()

    # Create extended client
    client = DisperserWithRetrieval(
        hostname=network_config.disperser_host,
        port=network_config.disperser_port,
        use_secure_grpc=True,
        signer=signer,
        payment_config=PaymentConfig(
            price_per_symbol=network_config.price_per_symbol,
            min_num_symbols=network_config.min_num_symbols,
        ),
    )

    # Prepare test data
    test_data = b"This is test data that we'll retrieve later!"
    print(f"Dispersing {len(test_data)} bytes of data...")

    try:
        # Disperse with header capture
        status, blob_key, blob_header, reference_block = client.disperse_blob_with_header(
            test_data, quorum_numbers=[0]  # Using quorum 0
        )

        if status == BlobStatus.QUEUED:
            print("✅ Blob dispersed successfully!")
            print(f"   Blob key: {blob_key.hex()}")
            print(f"   Reference block: {reference_block}")
            print(f"   Status: {status}")

            # Save metadata for retrieval
            metadata_file = save_blob_metadata(blob_key, blob_header, reference_block, quorum_id=0)

            print("\n📝 To retrieve this blob later:")
            print("1. Load the saved metadata")
            print("2. Use the blob_header and reference_block with a Retriever")
            print("3. Connect to an EigenDA node that has the data")

            # Show retrieval code
            print("\n```python")
            print("# Load metadata")
            print(f"with open('{metadata_file}', 'r') as f:")
            print("    metadata = json.load(f)")
            print("")
            print("# Initialize retriever")
            print("retriever = BlobRetriever(")
            print("    hostname='node.eigenda.xyz',  # EigenDA node address")
            print("    port=443,")
            print("    use_secure_grpc=True,")
            print("    signer=signer")
            print(")")
            print("")
            print("# Retrieve blob")
            print("encoded_data = retriever.retrieve_blob(")
            print("    blob_header=blob_header,  # Need the actual protobuf object")
            print("    reference_block_number=metadata['reference_block'],")
            print("    quorum_id=metadata['quorum_id']")
            print(")")
            print("")
            print("# Decode to original")
            print("original_data = decode_blob_data(encoded_data)")
            print("```")

        else:
            print(f"❌ Dispersal failed with status: {status}")

    except Exception as e:
        print(f"Error during dispersal: {e}")
    finally:
        client.close()

    print("\n" + "=" * 60)
    print("⚠️  IMPORTANT NOTES:")
    print("1. The retriever connects directly to EigenDA nodes, not the disperser")
    print("2. You need to know which nodes have your data (based on quorum)")
    print("3. The blob header must be properly serialized/deserialized")
    print("4. In production, use a database to store blob metadata")


if __name__ == "__main__":
    main()
