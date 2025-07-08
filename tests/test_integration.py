"""Integration tests for the EigenDA client."""

import os
import pytest
from eigenda import MockDisperserClient, LocalBlobRequestSigner
from eigenda.codec import encode_blob_data


class TestIntegration:
    """Integration tests that can be run against a real disperser."""

    @pytest.mark.skipif(
        not os.getenv("EIGENDA_PRIVATE_KEY"),
        reason="EIGENDA_PRIVATE_KEY not set"
    )
    def test_disperse_blob_real(self):
        """Test dispersing a blob to the real network."""
        private_key = os.getenv("EIGENDA_PRIVATE_KEY")
        signer = LocalBlobRequestSigner(private_key)

        client = MockDisperserClient(
            hostname="disperser-testnet-holesky.eigenda.xyz",
            port=443,
            use_secure_grpc=True,
            signer=signer
        )

        try:
            # Prepare test data
            test_data = b"Integration test from Python client"
            encoded_data = encode_blob_data(test_data)

            # Disperse blob
            status, blob_key = client.disperse_blob(
                data=encoded_data,
                blob_version=0,
                quorum_ids=[0, 1]
            )

            assert status is not None
            assert blob_key is not None
            assert len(bytes(blob_key)) == 32

        finally:
            client.close()

    def test_client_context_manager(self):
        """Test using client as context manager."""
        # Use a dummy signer for this test
        dummy_key = "0x" + "01" * 32
        signer = LocalBlobRequestSigner(dummy_key)

        with MockDisperserClient(
            hostname="example.com",
            port=443,
            use_secure_grpc=True,
            signer=signer
        ) as client:
            assert client._channel is None  # Not connected yet
            # Would connect on first use
