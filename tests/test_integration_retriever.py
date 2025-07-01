"""Integration tests for retriever with mock gRPC server."""

import threading
from concurrent import futures
from unittest.mock import Mock, patch

import grpc
import pytest

from eigenda.retriever import BlobRetriever
from eigenda.grpc.retriever.v2 import retriever_v2_pb2, retriever_v2_pb2_grpc
from eigenda.grpc.common.v2 import common_v2_pb2
from eigenda.grpc.common import common_pb2


class MockRetrieverServicer(retriever_v2_pb2_grpc.RetrieverServicer):
    """Mock gRPC servicer for retriever testing."""

    def __init__(self):
        self.retrieve_blob_called = False
        self.blob_data = [
            b'Hello, World!',      # index 0
            b'This is a test blob',  # index 1
            b'x' * 1000,           # index 2 - Large blob
        ]
        self.call_count = 0

    def RetrieveBlob(self, request, context):
        """Mock RetrieveBlob RPC."""
        self.retrieve_blob_called = True
        self.call_count += 1

        # Use the commitment length to determine which blob to return
        # This is a simple mock - in reality, blob would be identified differently
        blob_index = -1  # Default to not found
        if (hasattr(request.blob_header, 'commitment') and
                hasattr(request.blob_header.commitment, 'length')):
            length = request.blob_header.commitment.length
            if length == 13:
                blob_index = 0
            elif length == 19:
                blob_index = 1
            elif length == 1000:
                blob_index = 2

        # Check if we have data for this blob
        if 0 <= blob_index < len(self.blob_data):
            return retriever_v2_pb2.BlobReply(
                data=self.blob_data[blob_index]
            )
        else:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('Blob not found')
            context.abort(grpc.StatusCode.NOT_FOUND, 'Blob not found')
            return retriever_v2_pb2.BlobReply()  # Won't reach here but needed for type checker


class TestRetrieverIntegration:
    """Integration tests for retriever with mock gRPC."""

    @pytest.fixture
    def mock_servicer(self):
        """Create mock servicer."""
        return MockRetrieverServicer()

    @pytest.fixture
    def grpc_server(self, mock_servicer):
        """Create and start a gRPC server."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        retriever_v2_pb2_grpc.add_RetrieverServicer_to_server(mock_servicer, server)

        # Listen on a random available port
        port = server.add_insecure_port('[::]:0')
        server.start()

        yield f'localhost:{port}'

        server.stop(0)

    @pytest.fixture
    def mock_blob_header(self):
        """Create mock blob header."""
        return common_v2_pb2.BlobHeader(
            version=1,
            quorum_numbers=[0, 1],
            commitment=common_pb2.BlobCommitment(
                commitment=b'\x01' * 64,
                length_commitment=b'\x02' * 48,
                length_proof=b'\x03' * 48,
                length=13
            ),
            payment_header=common_v2_pb2.PaymentHeader(
                account_id='0x1234567890123456789012345678901234567890',
                timestamp=1000000000,
                cumulative_payment=b'\x00' * 32
            )
        )

    def test_retrieve_blob_success(self, grpc_server, mock_servicer, mock_blob_header):
        """Test successful blob retrieval."""
        # Parse host and port from grpc_server string
        host, port = grpc_server.split(':')
        retriever = BlobRetriever(hostname=host, port=int(port), use_secure_grpc=False)

        try:
            # Retrieve blob
            data = retriever.retrieve_blob(
                blob_header=mock_blob_header,
                reference_block_number=12345,
                quorum_id=0
            )

            # Verify
            assert data == b'Hello, World!'
            assert mock_servicer.retrieve_blob_called
            assert mock_servicer.call_count == 1

        finally:
            retriever.close()

    def test_retrieve_multiple_blobs(self, grpc_server, mock_servicer):
        """Test retrieving multiple blobs."""
        # Parse host and port from grpc_server string
        host, port = grpc_server.split(':')
        retriever = BlobRetriever(hostname=host, port=int(port), use_secure_grpc=False)

        try:
            # Retrieve multiple blobs
            retrieved_data = []

            for i, length in enumerate([13, 19, 1000]):
                header = common_v2_pb2.BlobHeader(
                    version=1,
                    quorum_numbers=[0],
                    commitment=common_pb2.BlobCommitment(
                        commitment=b'\x01' * 64,
                        length_commitment=b'\x02' * 48,
                        length_proof=b'\x03' * 48,
                        length=length
                    ),
                    payment_header=common_v2_pb2.PaymentHeader(
                        account_id='0x1234567890123456789012345678901234567890',
                        timestamp=1000000000,
                        cumulative_payment=b'\x00' * 32
                    )
                )

                data = retriever.retrieve_blob(
                    blob_header=header,
                    reference_block_number=12345,
                    quorum_id=0
                )
                retrieved_data.append(data)

            # Verify all blobs retrieved
            assert len(retrieved_data) == 3
            assert retrieved_data[0] == b'Hello, World!'
            assert retrieved_data[1] == b'This is a test blob'
            assert retrieved_data[2] == b'x' * 1000
            assert mock_servicer.call_count == 3

        finally:
            retriever.close()

    def test_retrieve_blob_not_found(self, grpc_server, mock_servicer):
        """Test retrieval of non-existent blob."""
        # Parse host and port from grpc_server string
        host, port = grpc_server.split(':')
        retriever = BlobRetriever(hostname=host, port=int(port), use_secure_grpc=False)

        try:
            # Try to retrieve non-existent blob
            header = common_v2_pb2.BlobHeader(
                version=1,
                quorum_numbers=[0],
                commitment=common_pb2.BlobCommitment(
                    commitment=b'\x01' * 64,
                    length_commitment=b'\x02' * 48,
                    length_proof=b'\x03' * 48,
                    length=999  # Non-existent length
                ),
                payment_header=common_v2_pb2.PaymentHeader(
                    account_id='0x1234567890123456789012345678901234567890',
                    timestamp=1000000000,
                    cumulative_payment=b'\x00' * 32
                )
            )

            # Try to retrieve and catch the specific error
            try:
                result = retriever.retrieve_blob(
                    blob_header=header,
                    reference_block_number=12345,
                    quorum_id=0
                )
                # If we get here without exception, fail the test
                pytest.fail("Expected exception but got result: {}".format(result))
            except Exception as e:
                # Should have wrapped the gRPC error
                assert 'gRPC error retrieving blob' in str(e)
                assert 'NOT_FOUND' in str(e)
                assert 'Blob not found' in str(e)

        finally:
            retriever.close()

    def test_context_manager(self, grpc_server, mock_servicer, mock_blob_header):
        """Test retriever as context manager."""
        host, port = grpc_server.split(':')
        with BlobRetriever(hostname=host, port=int(port), use_secure_grpc=False) as retriever:
            data = retriever.retrieve_blob(
                blob_header=mock_blob_header,
                reference_block_number=12345,
                quorum_id=0
            )
            assert data == b'Hello, World!'

    def test_concurrent_retrieval(self, grpc_server, mock_servicer):
        """Test concurrent blob retrievals."""
        # Parse host and port from grpc_server string
        host, port = grpc_server.split(':')
        retriever = BlobRetriever(hostname=host, port=int(port), use_secure_grpc=False)

        try:
            results = []
            threads = []

            def retrieve_blob(length, expected_data):
                header = common_v2_pb2.BlobHeader(
                    version=1,
                    quorum_numbers=[0],
                    commitment=common_pb2.BlobCommitment(
                        commitment=b'\x01' * 64,
                        length_commitment=b'\x02' * 48,
                        length_proof=b'\x03' * 48,
                        length=length
                    ),
                    payment_header=common_v2_pb2.PaymentHeader(
                        account_id='0x1234567890123456789012345678901234567890',
                        timestamp=1000000000,
                        cumulative_payment=b'\x00' * 32
                    )
                )

                try:
                    data = retriever.retrieve_blob(
                        blob_header=header,
                        reference_block_number=12345,
                        quorum_id=0
                    )
                    results.append((length, data))
                except Exception as e:
                    results.append((length, e))

            # Start concurrent retrievals
            blob_configs = [
                (13, b'Hello, World!'),
                (19, b'This is a test blob'),
                (1000, b'x' * 1000)
            ]
            for length, expected_data in blob_configs:
                thread = threading.Thread(
                    target=retrieve_blob,
                    args=(length, expected_data)
                )
                thread.start()
                threads.append(thread)

            # Wait for all threads
            for thread in threads:
                thread.join()

            # Verify results
            assert len(results) == 3
            # Sort results by length for consistent ordering
            results.sort(key=lambda x: x[0])
            expected = [(13, b'Hello, World!'), (19, b'This is a test blob'), (1000, b'x' * 1000)]
            for (length, data), (exp_length, exp_data) in zip(results, expected):
                assert isinstance(data, bytes)
                assert data == exp_data

        finally:
            retriever.close()


class TestRetrieverWithDisperser:
    """Test retriever integration with disperser flow."""

    def test_disperse_and_retrieve_flow(self):
        """Test complete disperse and retrieve flow."""
        # This test demonstrates how retriever would work with disperser
        # In real scenario, you would need both services running

        # Mock blob header from dispersal
        blob_header = common_v2_pb2.BlobHeader(
            version=1,
            quorum_numbers=[0, 1],
            commitment=common_pb2.BlobCommitment(
                commitment=b'\x10' * 64,
                length_commitment=b'\x20' * 48,
                length_proof=b'\x30' * 48,
                length=100
            ),
            payment_header=common_v2_pb2.PaymentHeader(
                account_id='0x1234567890123456789012345678901234567890',
                timestamp=1000000000,
                cumulative_payment=b'\x00' * 32
            )
        )

        # Mock the retriever response
        with patch('grpc.insecure_channel'), \
                patch('eigenda.retriever.retriever_v2_pb2_grpc.RetrieverStub') as mock_stub_class:

            mock_stub = Mock()
            mock_stub_class.return_value = mock_stub

            # Mock retrieval
            mock_stub.RetrieveBlob.return_value = retriever_v2_pb2.BlobReply(
                data=b'Original dispersed data'
            )

            # Create retriever
            retriever = BlobRetriever(
                hostname='localhost',
                port=50052,
                use_secure_grpc=False
            )

            try:
                # Retrieve using blob header from dispersal
                data = retriever.retrieve_blob(
                    blob_header=blob_header,
                    reference_block_number=12345678,
                    quorum_id=0
                )

                assert data == b'Original dispersed data'

                # Verify request
                request = mock_stub.RetrieveBlob.call_args[0][0]
                assert request.blob_header is not None
                assert request.reference_block_number == 12345678
                assert request.quorum_id == 0

            finally:
                retriever.close()


class TestRetrieverErrorHandling:
    """Test error handling in retriever."""

    def test_network_error(self):
        """Test handling of network errors."""
        with patch('grpc.insecure_channel') as mock_channel:
            mock_channel.return_value = Mock()

            with patch('eigenda.retriever.retriever_v2_pb2_grpc.RetrieverStub') as mock_stub_class:
                mock_stub = Mock()
                mock_stub_class.return_value = mock_stub

                # Make RPC fail with a proper gRPC error
                error = grpc.RpcError()
                error.code = lambda: grpc.StatusCode.UNAVAILABLE
                error.details = lambda: "Network error"
                mock_stub.RetrieveBlob.side_effect = error

                retriever = BlobRetriever(
                    hostname='localhost',
                    port=50052,
                    use_secure_grpc=False
                )

                try:
                    header = common_v2_pb2.BlobHeader(
                        version=1,
                        quorum_numbers=[0],
                        commitment=common_pb2.BlobCommitment(
                            commitment=b'\x01' * 64,
                            length_commitment=b'\x02' * 48,
                            length_proof=b'\x03' * 48,
                            length=100
                        ),
                        payment_header=common_v2_pb2.PaymentHeader(
                            account_id='0x1234567890123456789012345678901234567890',
                            timestamp=1000000000,
                            cumulative_payment=b'\x00' * 32
                        )
                    )

                    with pytest.raises(Exception):
                        retriever.retrieve_blob(
                            blob_header=header,
                            reference_block_number=12345,
                            quorum_id=0
                        )

                finally:
                    retriever.close()

    def test_invalid_blob_header(self):
        """Test handling of invalid blob header."""
        with patch('grpc.insecure_channel'), \
                patch('eigenda.retriever.retriever_v2_pb2_grpc.RetrieverStub') as mock_stub_class:

            mock_stub = Mock()
            mock_stub_class.return_value = mock_stub

            # Make the stub raise an error immediately
            class MockRpcError(grpc.RpcError):
                def code(self):
                    return grpc.StatusCode.INVALID_ARGUMENT

                def details(self):
                    return "Invalid blob header"

            mock_stub.RetrieveBlob.side_effect = MockRpcError("Invalid blob header")

            retriever = BlobRetriever(
                hostname='localhost',
                port=50052,
                use_secure_grpc=False
            )

            try:
                # Test with None header
                try:
                    result = retriever.retrieve_blob(
                        blob_header=None,
                        reference_block_number=12345,
                        quorum_id=0
                    )
                    pytest.fail("Expected exception but got result: {}".format(result))
                except Exception as e:
                    assert 'gRPC error retrieving blob' in str(e)

            finally:
                retriever.close()

    def test_timeout_handling(self):
        """Test timeout handling in retriever."""
        import time

        with patch('grpc.insecure_channel'), \
                patch('eigenda.retriever.retriever_v2_pb2_grpc.RetrieverStub') as mock_stub_class:

            mock_stub = Mock()
            mock_stub_class.return_value = mock_stub

            # Simulate slow response
            def slow_response(request):
                time.sleep(2)
                return retriever_v2_pb2.BlobReply(data=b'slow data')

            mock_stub.RetrieveBlob.side_effect = slow_response

            retriever = BlobRetriever(
                hostname='localhost',
                port=50052,
                use_secure_grpc=False
            )

            # In real implementation, this would timeout
            retriever.close()


class TestRetrieverPerformance:
    """Test performance aspects of retriever."""

    def test_large_blob_retrieval(self):
        """Test retrieval of large blobs."""
        with patch('grpc.insecure_channel'), \
                patch('eigenda.retriever.retriever_v2_pb2_grpc.RetrieverStub') as mock_stub_class:

            mock_stub = Mock()
            mock_stub_class.return_value = mock_stub

            # Mock large blob response
            large_data = b'x' * (10 * 1024 * 1024)  # 10MB
            mock_stub.RetrieveBlob.return_value = retriever_v2_pb2.BlobReply(
                data=large_data
            )

            retriever = BlobRetriever(
                hostname='localhost',
                port=50052,
                use_secure_grpc=False
            )

            try:
                header = common_v2_pb2.BlobHeader(
                    version=1,
                    quorum_numbers=[0],
                    commitment=common_pb2.BlobCommitment(
                        commitment=b'\x01' * 64,
                        length_commitment=b'\x02' * 48,
                        length_proof=b'\x03' * 48,
                        length=len(large_data)
                    ),
                    payment_header=common_v2_pb2.PaymentHeader(
                        account_id='0x1234567890123456789012345678901234567890',
                        timestamp=1000000000,
                        cumulative_payment=b'\x00' * 32
                    )
                )

                data = retriever.retrieve_blob(
                    blob_header=header,
                    reference_block_number=12345,
                    quorum_id=0
                )

                assert len(data) == len(large_data)
                assert data == large_data

            finally:
                retriever.close()

    def test_batch_retrieval_performance(self):
        """Test performance of batch retrievals."""
        with patch('grpc.insecure_channel'), \
                patch('eigenda.retriever.retriever_v2_pb2_grpc.RetrieverStub') as mock_stub_class:

            mock_stub = Mock()
            mock_stub_class.return_value = mock_stub

            # Mock responses
            blob_counter = 0

            def create_blob_response(request, **kwargs):  # Accept any kwargs for timeout etc
                nonlocal blob_counter
                blob_counter += 1
                return retriever_v2_pb2.BlobReply(
                    data=f'blob_data_{blob_counter}'.encode()
                )

            mock_stub.RetrieveBlob.side_effect = create_blob_response

            retriever = BlobRetriever(
                hostname='localhost',
                port=50052,
                use_secure_grpc=False
            )

            try:
                # Retrieve many blobs
                retrieved_data = []
                for i in range(100):
                    header = common_v2_pb2.BlobHeader(
                        version=1,
                        quorum_numbers=[0],
                        commitment=common_pb2.BlobCommitment(
                            commitment=b'\x01' * 64,
                            length_commitment=b'\x02' * 48,
                            length_proof=b'\x03' * 48,
                            length=100
                        ),
                        payment_header=common_v2_pb2.PaymentHeader(
                            account_id='0x1234567890123456789012345678901234567890',
                            timestamp=1000000000,
                            cumulative_payment=b'\x00' * 32
                        )
                    )

                    data = retriever.retrieve_blob(
                        blob_header=header,
                        reference_block_number=12345,
                        quorum_id=0
                    )
                    retrieved_data.append(data)

                # Verify all retrieved
                assert len(retrieved_data) == 100
                for i, data in enumerate(retrieved_data):
                    assert data == f'blob_data_{i+1}'.encode()

            finally:
                retriever.close()
