"""
Example of retrieving a blob from EigenDA using the Retriever.

Note: The retriever requires:
1. The full blob header from when the blob was dispersed
2. The Ethereum block number at the time of dispersal
3. The quorum ID to retrieve from

This is different from simply using a blob key - you need to store
these values when you disperse a blob if you want to retrieve it later.
"""

import os
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.retriever import BlobRetriever

# For demonstration purposes, we'll show the structure needed
# In practice, you would get these from a previous dispersal


def retrieve_blob_example():
    """Example of retrieving a blob from EigenDA nodes."""

    # Initialize signer (optional - only needed if retriever requires auth)
    private_key = os.getenv("EIGENDA_PRIVATE_KEY")
    if private_key:
        signer = LocalBlobRequestSigner(private_key)
    else:
        signer = None
        print("Warning: No private key provided, using retriever without authentication")

    # Initialize retriever
    # Note: You need to know which node(s) to retrieve from
    # This is typically provided by the EigenDA network configuration
    retriever = BlobRetriever(
        hostname="retriever.eigenda.xyz",  # Replace with actual retriever endpoint
        port=443,
        use_secure_grpc=True,
        signer=signer
    )

    # To retrieve a blob, you need:
    # 1. The blob header from when it was dispersed
    # 2. The reference block number
    # 3. The quorum ID

    # Example: If you previously dispersed a blob and saved these values:
    """
    # From a previous dispersal:
    status, blob_key = client.disperse_blob(data)

    # You would also need to save:
    blob_header = <the blob header used in dispersal>
    reference_block = <current Ethereum block number>
    quorum_id = 0  # or whichever quorum you used
    """

    # For this example, we'll show the structure:
    # blob_header = <your saved blob header>
    # reference_block = 12345678  # The Ethereum block when blob was dispersed
    # quorum_id = 0  # The quorum to retrieve from

    try:
        # Retrieve the blob
        # encoded_data = retriever.retrieve_blob(blob_header, reference_block, quorum_id)

        # Decode the retrieved data
        # original_data = decode_blob_data(encoded_data)

        # print(f"Successfully retrieved blob: {len(original_data)} bytes")
        # print(f"Data preview: {original_data[:100]}...")

        print("\nNOTE: This is a demonstration of the retriever API.")
        print("To actually retrieve a blob, you need:")
        print("1. The complete blob header from dispersal")
        print("2. The Ethereum block number when the blob was dispersed")
        print("3. The quorum ID to retrieve from")
        print("\nThese values must be saved when you disperse a blob.")

    except Exception as e:
        print(f"Error retrieving blob: {e}")
    finally:
        retriever.close()


def retrieve_with_context_manager():
    """Example using context manager for automatic cleanup."""

    # Using context manager ensures the connection is closed
    with BlobRetriever(
        hostname="retriever.eigenda.xyz",
        port=443,
        use_secure_grpc=True
    ):
        print("Retriever connected and ready")
        # Perform retrieval operations here
        # ...


def full_dispersal_and_retrieval_flow():
    """
    Example showing the full flow of dispersing and then retrieving a blob.

    IMPORTANT: In a real application, you would need to:
    1. Disperse the blob
    2. Save the blob header, block number, and blob key
    3. Later use those saved values to retrieve the blob
    """

    print("\n=== Full Dispersal and Retrieval Flow ===\n")

    print("Step 1: Disperse a blob")
    print("```python")
    print("from eigenda.client_v2_full import DisperserClientV2Full")
    print("from eigenda.auth.signer import LocalBlobRequestSigner")
    print("")
    print("# Initialize client")
    print("signer = LocalBlobRequestSigner(private_key)")
    print("client = DisperserClientV2Full(...)")
    print("")
    print("# Disperse blob")
    print("data = b'Hello, EigenDA!'")
    print("status, blob_key = client.disperse_blob(data)")
    print("")
    print("# IMPORTANT: Save these for retrieval!")
    print("# You need to capture the blob header from the dispersal")
    print("# This requires modifying the client to return it")
    print("```")
    print("")
    print("Step 2: Save retrieval information")
    print("```python")
    print("# Save for later retrieval:")
    print("retrieval_info = {")
    print("    'blob_key': blob_key.hex(),")
    print("    'blob_header': blob_header,  # Need to get this from dispersal")
    print("    'reference_block': current_block_number,")
    print("    'quorum_id': 0")
    print("}")
    print("```")
    print("")
    print("Step 3: Retrieve the blob later")
    print("```python")
    print("from eigenda.retriever import BlobRetriever")
    print("")
    print("retriever = BlobRetriever(...)")
    print("encoded_data = retriever.retrieve_blob(")
    print("    blob_header=retrieval_info['blob_header'],")
    print("    reference_block_number=retrieval_info['reference_block'],")
    print("    quorum_id=retrieval_info['quorum_id']")
    print(")")
    print("")
    print("# Decode to get original data")
    print("original_data = decode_blob_data(encoded_data)")
    print("```")


if __name__ == "__main__":
    print("EigenDA Blob Retrieval Example")
    print("=" * 40)

    # Show basic retrieval example
    retrieve_blob_example()

    print("\n" + "=" * 40)

    # Show full flow
    full_dispersal_and_retrieval_flow()

    print("\n" + "=" * 40)
    print("\nNOTE: The current retriever implementation requires the full blob header")
    print("from dispersal, not just the blob key. This means you need to modify")
    print("the disperser client to return and save the blob header for later retrieval.")
