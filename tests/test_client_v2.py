"""Tests for the v2 disperser client."""

import pytest
from unittest.mock import Mock, patch
from eigenda import DisperserClientV2, LocalBlobRequestSigner


class TestDisperserClientV2:
    """Test v2 disperser client functionality."""

    @pytest.fixture
    def mock_signer(self):
        """Create a mock signer."""
        signer = Mock(spec=LocalBlobRequestSigner)
        signer.get_account_id.return_value = "0x1234567890123456789012345678901234567890"
        signer.sign_blob_request.return_value = b"mock_signature" * 4  # 64 bytes
        signer.sign_payment_state_request.return_value = b"mock_signature" * 4
        return signer

    @pytest.fixture
    def client(self, mock_signer):
        """Create a test client."""
        return DisperserClientV2(
            hostname="test.disperser.com",
            port=443,
            use_secure_grpc=True,
            signer=mock_signer
        )

    def test_client_creation(self, mock_signer):
        """Test creating a client."""
        client = DisperserClientV2(
            hostname="test.disperser.com",
            port=443,
            use_secure_grpc=True,
            signer=mock_signer
        )

        assert client.hostname == "test.disperser.com"
        assert client.port == 443
        assert client.use_secure_grpc is True
        assert client.signer == mock_signer
        assert client._channel is None
        assert client._stub is None
        assert client._connected is False

    def test_context_manager(self, client):
        """Test using client as context manager."""
        with client as c:
            assert c == client

        # After exiting, should be closed
        assert client._connected is False
        assert client._channel is None

    def test_validate_data(self, client):
        """Test data validation in disperse_blob."""
        # Empty data should raise
        with pytest.raises(ValueError, match="Data cannot be empty"):
            client.disperse_blob(b"", 0, [0, 1])

        # Too large data should raise
        large_data = b"x" * (16 * 1024 * 1024 + 1)
        with pytest.raises(ValueError, match="Data exceeds maximum size"):
            client.disperse_blob(large_data, 0, [0, 1])

    @patch('eigenda.client_v2.grpc.secure_channel')
    def test_secure_connection(self, mock_channel, client):
        """Test establishing secure gRPC connection."""
        mock_channel.return_value = Mock()

        client._connect()

        assert client._connected is True
        mock_channel.assert_called_once()
        args, kwargs = mock_channel.call_args
        assert args[0] == "test.disperser.com:443"

    @patch('eigenda.client_v2.grpc.insecure_channel')
    def test_insecure_connection(self, mock_channel, mock_signer):
        """Test establishing insecure gRPC connection."""
        client = DisperserClientV2(
            hostname="localhost",
            port=50051,
            use_secure_grpc=False,
            signer=mock_signer
        )

        mock_channel.return_value = Mock()

        client._connect()

        assert client._connected is True
        mock_channel.assert_called_once()
        args, kwargs = mock_channel.call_args
        assert args[0] == "localhost:50051"
