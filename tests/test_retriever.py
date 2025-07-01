"""Tests for blob retrieval functionality."""

import pytest
from unittest.mock import Mock, MagicMock, patch
import grpc

from eigenda.retriever import (
    BlobRetriever,
    RetrieverConfig
)
from eigenda.auth.signer import LocalBlobRequestSigner


class TestRetrieverConfig:
    """Test the RetrieverConfig dataclass."""
    
    def test_config_creation(self):
        """Test creating retriever configuration."""
        config = RetrieverConfig(
            hostname="retriever.example.com",
            port=443,
            use_secure_grpc=True,
            timeout=120
        )
        
        assert config.hostname == "retriever.example.com"
        assert config.port == 443
        assert config.use_secure_grpc is True
        assert config.timeout == 120
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = RetrieverConfig(
            hostname="retriever.example.com",
            port=443
        )
        
        assert config.use_secure_grpc is True
        assert config.timeout == 60


class TestBlobRetriever:
    """Test the BlobRetriever client."""
    
    @pytest.fixture
    def mock_signer(self):
        """Create a mock signer."""
        signer = Mock(spec=LocalBlobRequestSigner)
        signer.get_account_id.return_value = "0x1234567890123456789012345678901234567890"
        return signer
    
    @pytest.fixture
    def mock_grpc(self):
        """Mock gRPC dependencies."""
        with patch('eigenda.retriever.grpc.secure_channel'), \
             patch('eigenda.retriever.grpc.insecure_channel'), \
             patch('eigenda.retriever.retriever_v2_pb2_grpc.RetrieverStub'):
            yield
    
    @pytest.fixture
    def retriever(self, mock_signer, mock_grpc):
        """Create a retriever instance with mocked gRPC."""
        return BlobRetriever(
            hostname="retriever.example.com",
            port=443,
            use_secure_grpc=True,
            signer=mock_signer
        )
    
    @pytest.fixture
    def mock_blob_header(self):
        """Create a mock blob header."""
        header = Mock()
        header.version = 0
        header.quorum_numbers = [0, 1]
        header.commitment = Mock()
        header.payment_header = Mock()
        return header
    
    def test_retriever_creation_with_config(self, mock_signer, mock_grpc):
        """Test creating retriever with explicit config."""
        config = RetrieverConfig(
            hostname="retriever.example.com",
            port=443,
            use_secure_grpc=False,
            timeout=90
        )
        
        retriever = BlobRetriever(
            hostname="retriever.example.com",
            port=443,
            use_secure_grpc=False,
            signer=mock_signer,
            config=config
        )
        
        assert retriever.hostname == "retriever.example.com"
        assert retriever.port == 443
        assert retriever.use_secure_grpc is False
        assert retriever.signer == mock_signer
        assert retriever.config.timeout == 90
        assert not retriever._connected
    
    def test_retriever_creation_without_signer(self, mock_grpc):
        """Test creating retriever without signer."""
        retriever = BlobRetriever(
            hostname="retriever.example.com",
            port=443,
            use_secure_grpc=True
        )
        
        assert retriever.signer is None
        assert retriever.config.hostname == "retriever.example.com"
    
    def test_connect_secure(self, retriever):
        """Test establishing secure gRPC connection."""
        mock_channel = Mock()
        mock_stub = Mock()
        
        with patch('eigenda.retriever.grpc.ssl_channel_credentials') as mock_creds, \
             patch('eigenda.retriever.grpc.secure_channel', return_value=mock_channel) as mock_secure, \
             patch('eigenda.retriever.retriever_v2_pb2_grpc.RetrieverStub', return_value=mock_stub):
            
            retriever._connect()
            
            # Verify secure channel creation
            mock_creds.assert_called_once()
            mock_secure.assert_called_once_with(
                "retriever.example.com:443",
                mock_creds.return_value,
                [
                    ('grpc.max_receive_message_length', 32 * 1024 * 1024),
                    ('grpc.max_send_message_length', 1 * 1024 * 1024),
                ]
            )
            
            assert retriever._channel == mock_channel
            assert retriever._stub == mock_stub
            assert retriever._connected is True
    
    def test_connect_insecure(self, mock_signer, mock_grpc):
        """Test establishing insecure gRPC connection."""
        retriever = BlobRetriever(
            hostname="localhost",
            port=8080,
            use_secure_grpc=False,
            signer=mock_signer
        )
        
        mock_channel = Mock()
        mock_stub = Mock()
        
        with patch('eigenda.retriever.grpc.insecure_channel', return_value=mock_channel) as mock_insecure, \
             patch('eigenda.retriever.retriever_v2_pb2_grpc.RetrieverStub', return_value=mock_stub):
            
            retriever._connect()
            
            # Verify insecure channel creation
            mock_insecure.assert_called_once_with(
                "localhost:8080",
                [
                    ('grpc.max_receive_message_length', 32 * 1024 * 1024),
                    ('grpc.max_send_message_length', 1 * 1024 * 1024),
                ]
            )
            
            assert retriever._connected is True
    
    def test_connect_idempotent(self, retriever):
        """Test that connect is idempotent."""
        mock_channel = Mock()
        
        with patch('eigenda.retriever.grpc.ssl_channel_credentials'), \
             patch('eigenda.retriever.grpc.secure_channel', return_value=mock_channel) as mock_secure, \
             patch('eigenda.retriever.retriever_v2_pb2_grpc.RetrieverStub'):
            
            # First connect
            retriever._connect()
            assert mock_secure.call_count == 1
            
            # Second connect should not create new channel
            retriever._connect()
            assert mock_secure.call_count == 1
    
    def test_retrieve_blob_success(self, retriever, mock_blob_header):
        """Test successful blob retrieval."""
        expected_data = b'test blob data'
        reference_block = 12345
        quorum_id = 0
        
        # Mock the gRPC response
        mock_response = Mock()
        mock_response.data = expected_data
        
        # Mock the request creation
        mock_request = Mock()
        with patch('eigenda.retriever.retriever_v2_pb2.BlobRequest', return_value=mock_request):
            # Set up the stub
            retriever._stub = Mock()
            retriever._stub.RetrieveBlob.return_value = mock_response
            retriever._connected = True
            
            # Retrieve blob
            data = retriever.retrieve_blob(mock_blob_header, reference_block, quorum_id)
        
        assert data == expected_data
        
        # The mock was created inside the patch context, so we can't verify it directly
        
        # Verify the gRPC call
        retriever._stub.RetrieveBlob.assert_called_once_with(
            mock_request,
            timeout=60,
            metadata=[
                ('user-agent', 'eigenda-python-retriever/0.1.0'),
                ('account-id', '0x1234567890123456789012345678901234567890')
            ]
        )
    
    def test_retrieve_blob_grpc_error(self, retriever, mock_blob_header):
        """Test blob retrieval with gRPC error."""
        reference_block = 12345
        quorum_id = 0
        
        # Mock the request
        mock_request = Mock()
        with patch('eigenda.retriever.retriever_v2_pb2.BlobRequest', return_value=mock_request):
            # Mock gRPC error
            retriever._stub = Mock()
            error = grpc.RpcError()
            error.code = lambda: grpc.StatusCode.NOT_FOUND
            error.details = lambda: "Blob not found"
            retriever._stub.RetrieveBlob.side_effect = error
            retriever._connected = True
            
            # Should raise exception
            with pytest.raises(Exception, match="gRPC error retrieving blob"):
                retriever.retrieve_blob(mock_blob_header, reference_block, quorum_id)
    
    def test_get_metadata_with_signer(self, retriever):
        """Test metadata generation with signer."""
        metadata = retriever._get_metadata()
        
        assert metadata == [
            ('user-agent', 'eigenda-python-retriever/0.1.0'),
            ('account-id', '0x1234567890123456789012345678901234567890')
        ]
    
    def test_get_metadata_without_signer(self, mock_grpc):
        """Test metadata generation without signer."""
        retriever = BlobRetriever(
            hostname="retriever.example.com",
            port=443,
            use_secure_grpc=True
        )
        
        metadata = retriever._get_metadata()
        
        assert metadata == [
            ('user-agent', 'eigenda-python-retriever/0.1.0')
        ]
    
    def test_close(self, retriever):
        """Test closing the connection."""
        # Set up a connected state
        mock_channel = Mock()
        retriever._channel = mock_channel
        retriever._stub = Mock()
        retriever._connected = True
        
        # Close the connection
        retriever.close()
        
        # Verify cleanup
        mock_channel.close.assert_called_once()
        assert retriever._connected is False
        assert retriever._channel is None
        assert retriever._stub is None
    
    def test_close_no_channel(self, retriever):
        """Test closing when no channel exists."""
        # Should not raise error
        retriever.close()
        assert retriever._connected is False
    
    def test_context_manager(self, retriever):
        """Test using retriever as context manager."""
        mock_channel = Mock()
        retriever._channel = mock_channel
        retriever._connected = True
        
        with retriever as r:
            assert r == retriever
        
        # Should be closed after context
        mock_channel.close.assert_called_once()
        assert retriever._connected is False
    
    def test_retrieve_blob_with_custom_timeout(self, retriever, mock_blob_header):
        """Test blob retrieval with custom timeout."""
        # Update timeout
        retriever.config.timeout = 120
        
        expected_data = b'test blob data'
        reference_block = 12345
        quorum_id = 0
        
        # Mock the gRPC response
        mock_response = Mock()
        mock_response.data = expected_data
        
        # Mock the request
        mock_request = Mock()
        with patch('eigenda.retriever.retriever_v2_pb2.BlobRequest', return_value=mock_request):
            # Set up the stub
            retriever._stub = Mock()
            retriever._stub.RetrieveBlob.return_value = mock_response
            retriever._connected = True
            
            # Retrieve blob
            data = retriever.retrieve_blob(mock_blob_header, reference_block, quorum_id)
        
        # Verify custom timeout was used
        call_args = retriever._stub.RetrieveBlob.call_args
        assert call_args[1]['timeout'] == 120
    
    def test_large_blob_retrieval(self, retriever, mock_blob_header):
        """Test retrieving a large blob."""
        reference_block = 12345
        quorum_id = 0
        
        # Create a 10MB blob
        large_data = b'x' * (10 * 1024 * 1024)
        
        # Mock the gRPC response
        mock_response = Mock()
        mock_response.data = large_data
        
        # Mock the request
        mock_request = Mock()
        with patch('eigenda.retriever.retriever_v2_pb2.BlobRequest', return_value=mock_request):
            # Set up the stub
            retriever._stub = Mock()
            retriever._stub.RetrieveBlob.return_value = mock_response
            retriever._connected = True
            
            # Retrieve blob
            data = retriever.retrieve_blob(mock_blob_header, reference_block, quorum_id)
        
        assert data == large_data
        assert len(data) == 10 * 1024 * 1024
    
    def test_retrieve_blob_connects_if_needed(self, retriever, mock_blob_header):
        """Test that retrieve_blob connects if not already connected."""
        expected_data = b'test blob data'
        reference_block = 12345
        quorum_id = 0
        
        # Mock the connection and response
        mock_channel = Mock()
        mock_stub = Mock()
        mock_response = Mock()
        mock_response.data = expected_data
        mock_stub.RetrieveBlob.return_value = mock_response
        
        with patch('eigenda.retriever.grpc.ssl_channel_credentials'), \
             patch('eigenda.retriever.grpc.secure_channel', return_value=mock_channel), \
             patch('eigenda.retriever.retriever_v2_pb2_grpc.RetrieverStub', return_value=mock_stub), \
             patch('eigenda.retriever.retriever_v2_pb2.BlobRequest'):
            
            # Ensure not connected
            assert not retriever._connected
            
            # Retrieve blob (should connect automatically)
            data = retriever.retrieve_blob(mock_blob_header, reference_block, quorum_id)
            
            assert retriever._connected is True
            assert data == expected_data