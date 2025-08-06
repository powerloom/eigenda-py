"""Tests for the mock DisperserClient to achieve 100% coverage."""

from unittest.mock import Mock, patch

import pytest

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client import DisperserClient as MockDisperserClient
from eigenda.client import DisperserClientConfig
from eigenda.core.types import BlobKey, BlobStatus


class TestMockDisperserClient:
    """Comprehensive tests for the mock disperser client."""

    @pytest.fixture
    def mock_signer(self):
        """Create a mock signer."""
        signer = Mock(spec=LocalBlobRequestSigner)
        signer.account = Mock()
        signer.account.address = "0x1234567890123456789012345678901234567890"
        return signer

    @pytest.fixture
    def client(self, mock_signer):
        """Create a mock client instance."""
        return MockDisperserClient(
            hostname="localhost", port=50051, use_secure_grpc=False, signer=mock_signer
        )

    def test_client_creation_with_signer(self, mock_signer):
        """Test client creation with signer."""
        client = MockDisperserClient(
            hostname="localhost", port=50051, use_secure_grpc=True, signer=mock_signer
        )
        assert client.hostname == "localhost"
        assert client.port == 50051
        assert client.use_secure_grpc is True
        assert client.signer is mock_signer

    def test_disperse_blob_complete_flow(self, client):
        """Test the complete disperse_blob flow."""
        # Test data
        data = b"Hello, EigenDA!"
        blob_version = 0
        quorum_ids = [0, 1]

        # Call disperse_blob
        status, blob_key = client.disperse_blob(
            data=data, blob_version=blob_version, quorum_ids=quorum_ids, timeout=30
        )

        # Verify results
        assert status == BlobStatus.QUEUED
        assert isinstance(blob_key, BlobKey)
        assert len(bytes(blob_key)) == 32

        # The blob key calculation in the mock client uses SHA3-256 and includes timestamp
        # so we can't verify the exact value, but we can verify it's different each time
        status2, blob_key2 = client.disperse_blob(data, blob_version, quorum_ids)
        assert bytes(blob_key) != bytes(blob_key2)  # Different due to timestamp

    def test_disperse_blob_empty_data(self, client):
        """Test dispersing empty data."""
        with pytest.raises(ValueError, match="Data cannot be empty"):
            client.disperse_blob(data=b"", blob_version=0, quorum_ids=[0])

    def test_disperse_blob_different_inputs(self, client):
        """Test that different inputs produce different blob keys."""
        # First blob
        status1, key1 = client.disperse_blob(data=b"data1", blob_version=0, quorum_ids=[0])

        # Second blob with different data
        status2, key2 = client.disperse_blob(data=b"data2", blob_version=0, quorum_ids=[0])

        # Third blob with different version
        status3, key3 = client.disperse_blob(data=b"data1", blob_version=1, quorum_ids=[0])

        # Fourth blob with different quorums
        status4, key4 = client.disperse_blob(data=b"data1", blob_version=0, quorum_ids=[0, 1])

        # All should be successful
        assert all(s == BlobStatus.QUEUED for s in [status1, status2, status3, status4])

        # All keys should be different
        keys = [key1, key2, key3, key4]
        assert len(set(bytes(k) for k in keys)) == 4

    def test_get_blob_status(self, client):
        """Test get_blob_status method."""
        # First disperse a blob
        _, blob_key = client.disperse_blob(data=b"test data", blob_version=0, quorum_ids=[0])

        # Get status
        status = client.get_blob_status(blob_key)

        # Mock always returns COMPLETE
        assert status == BlobStatus.COMPLETE

    def test_get_blob_status_with_different_keys(self, client):
        """Test get_blob_status with different keys."""
        # Create different blob keys
        key1 = BlobKey(b"a" * 32)
        key2 = BlobKey(b"b" * 32)

        # Both should return COMPLETE
        assert client.get_blob_status(key1) == BlobStatus.COMPLETE
        assert client.get_blob_status(key2) == BlobStatus.COMPLETE

    def test_close_method(self, client):
        """Test close method."""
        # Close should work without error
        client.close()

        # Can be called multiple times
        client.close()
        client.close()

    def test_context_manager(self, mock_signer):
        """Test using client as context manager."""
        blob_key = None

        with MockDisperserClient(
            hostname="localhost", port=50051, use_secure_grpc=False, signer=mock_signer
        ) as client:
            # Use client inside context
            status, blob_key = client.disperse_blob(
                data=b"context test", blob_version=0, quorum_ids=[0]
            )
            assert status == BlobStatus.QUEUED
            assert isinstance(blob_key, BlobKey)

        # Client should be closed after context
        # (Mock client doesn't have state to check, but close was called)
        assert blob_key is not None

    def test_context_manager_with_exception(self, mock_signer):
        """Test context manager handles exceptions properly."""
        with pytest.raises(ValueError):
            with MockDisperserClient(
                hostname="localhost", port=50051, use_secure_grpc=False, signer=mock_signer
            ) as client:
                # Do something
                status, _ = client.disperse_blob(b"test", 0, [0])
                assert status == BlobStatus.QUEUED

                # Raise exception
                raise ValueError("Test exception")

        # Context manager should have called close despite exception

    def test_private_calculate_blob_key(self, client):
        """Test the private _calculate_blob_key method."""
        # Test with various inputs
        test_cases = [
            (b"hello", 0, [0]),
            (b"world", 1, [1]),
            (b"x" * 1000, 42, [0, 1, 2, 3]),
        ]

        for data, version, quorums in test_cases:
            key = client._calculate_blob_key(data, version, quorums)

            # Should return a BlobKey
            assert isinstance(key, BlobKey)

            # Should be 32 bytes
            assert len(bytes(key)) == 32

            # Should be non-deterministic due to timestamp
            key2 = client._calculate_blob_key(data, version, quorums)
            assert bytes(key) != bytes(key2)

    def test_disperse_blob_data_size_limits(self, client):
        """Test data size validation."""
        # Test max size (16 MiB)
        max_data = b"x" * (16 * 1024 * 1024)
        status, blob_key = client.disperse_blob(max_data, 0, [0])
        assert status == BlobStatus.QUEUED

        # Test exceeding max size
        too_large_data = b"x" * (16 * 1024 * 1024 + 1)
        with pytest.raises(ValueError, match="Data exceeds maximum size"):
            client.disperse_blob(too_large_data, 0, [0])

    def test_large_data_handling(self, client):
        """Test handling of large data blobs."""
        # 10MB of data
        large_data = b"x" * (10 * 1024 * 1024)

        status, blob_key = client.disperse_blob(
            data=large_data, blob_version=0, quorum_ids=[0], timeout=60
        )

        assert status == BlobStatus.QUEUED
        assert isinstance(blob_key, BlobKey)

    def test_timeout_parameter(self, client):
        """Test that timeout parameter is accepted."""
        # Various timeout values
        for timeout in [None, 10, 30, 100]:
            status, blob_key = client.disperse_blob(
                data=b"timeout test", blob_version=0, quorum_ids=[0], timeout=timeout
            )
            assert status == BlobStatus.QUEUED

    def test_client_with_config(self, mock_signer):
        """Test client creation with explicit config."""
        config = DisperserClientConfig(
            hostname="test.host", port=443, use_secure_grpc=True, timeout=60
        )

        client = MockDisperserClient(
            hostname="localhost",
            port=50051,
            use_secure_grpc=False,
            signer=mock_signer,
            config=config,
        )

        # Client should use the provided config
        assert client.config == config
        assert client.config.timeout == 60

    def test_connect_multiple_times(self, client):
        """Test that _connect is idempotent."""
        # First connection
        client._connect()
        assert client._connected is True
        first_channel = client._channel

        # Second connection should not create new channel
        client._connect()
        assert client._connected is True
        assert client._channel is first_channel

    def test_secure_grpc_connection(self, mock_signer):
        """Test secure gRPC connection."""
        client = MockDisperserClient(
            hostname="secure.host", port=443, use_secure_grpc=True, signer=mock_signer
        )

        # Should create secure channel
        with patch("grpc.secure_channel") as mock_secure:
            with patch("grpc.ssl_channel_credentials") as mock_creds:
                client._connect()
                mock_creds.assert_called_once()
                mock_secure.assert_called_once_with("secure.host:443", mock_creds.return_value)

    def test_insecure_grpc_connection(self, client):
        """Test insecure gRPC connection."""
        # Should create insecure channel
        with patch("grpc.insecure_channel") as mock_insecure:
            client._connect()
            mock_insecure.assert_called_once_with("localhost:50051")
