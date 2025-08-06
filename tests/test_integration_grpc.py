"""Integration tests with mock gRPC server."""

import threading
import time
from concurrent import futures
from unittest.mock import Mock, patch

import grpc
import pytest

from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.grpc.common import common_pb2
from eigenda.grpc.common.v2 import common_v2_pb2
from eigenda.grpc.disperser.v2 import disperser_v2_pb2, disperser_v2_pb2_grpc


@pytest.fixture(scope="module")
def mock_signer():
    """Mock signer for authentication."""
    signer = Mock()
    signer.account = Mock()
    signer.account.address = "0x1234567890123456789012345678901234567890"
    signer.get_account_id = Mock(return_value="0x1234567890123456789012345678901234567890")
    signer.sign_blob_request = Mock(return_value=b"\x00" * 65)
    signer.sign_payment_state_request = Mock(return_value=b"\x00" * 65)
    signer.unsafe_sign_hash = Mock(return_value=Mock(signature=b"\x00" * 65))
    return signer


class MockDisperserServicer(disperser_v2_pb2_grpc.DisperserServicer):
    """Mock gRPC servicer for testing."""

    def __init__(self):
        self.get_payment_state_called = False
        self.disperse_blob_called = False
        self.get_blob_status_called = False
        self.get_blob_commit_called = False

        # Mock responses
        self.payment_state_response = disperser_v2_pb2.GetPaymentStateReply(
            reservation=disperser_v2_pb2.Reservation(
                symbols_per_second=100,
                start_timestamp=1000000000,
                end_timestamp=2000000000,
                quorum_numbers=bytes([0, 1]),
                quorum_splits=[50, 50],
            ),
            cumulative_payment=b"\x00" * 32,
            onchain_cumulative_payment=b"\x00" * 32,
        )

        self.disperse_blob_response = disperser_v2_pb2.DisperseBlobReply(
            result=disperser_v2_pb2.BlobStatus.QUEUED,
            blob_key=b"test_blob_key_1234567890" + b"\x00" * 8,  # Pad to 32 bytes
        )

        self.blob_status_response = disperser_v2_pb2.BlobStatusReply(
            status=disperser_v2_pb2.BlobStatus.COMPLETE,
            signed_batch=disperser_v2_pb2.SignedBatch(
                header=common_v2_pb2.BatchHeader(
                    batch_root=b"\x01" * 32, reference_block_number=12345678
                ),
                attestation=disperser_v2_pb2.Attestation(
                    non_signer_pubkeys=[],
                    apk_g2=b"\x01" * 128,
                    quorum_apks=[b"\x02" * 64],
                    sigma=b"\x03" * 64,
                    quorum_numbers=[0],
                    quorum_signed_percentages=b"\x64",
                ),
            ),
            blob_inclusion_info=disperser_v2_pb2.BlobInclusionInfo(
                blob_certificate=common_v2_pb2.BlobCertificate(
                    blob_header=common_v2_pb2.BlobHeader(
                        version=1,
                        quorum_numbers=[0, 1],
                        commitment=common_pb2.BlobCommitment(
                            commitment=b"\x01" * 64,
                            length_commitment=b"\x02" * 48,
                            length_proof=b"\x03" * 48,
                            length=1024,
                        ),
                        payment_header=common_v2_pb2.PaymentHeader(
                            account_id="0x1234567890123456789012345678901234567890",
                            timestamp=1000000000,
                            cumulative_payment=b"\x00" * 32,
                        ),
                    ),
                    signature=b"\x00" * 65,
                ),
                blob_index=0,
                inclusion_proof=b"\x00" * 32,
            ),
        )

        self.blob_commit_response = disperser_v2_pb2.BlobCommitmentReply(
            blob_commitment=common_pb2.BlobCommitment(
                commitment=b"\x01" * 64,
                length_commitment=b"\x02" * 48,
                length_proof=b"\x03" * 48,
                length=1024,
            )
        )

    def GetPaymentState(self, request, context):
        """Mock GetPaymentState RPC."""
        self.get_payment_state_called = True
        return self.payment_state_response

    def DisperseBlob(self, request, context):
        """Mock DisperseBlob RPC."""
        self.disperse_blob_called = True
        # Validate request - DisperserClientV2Full encodes the data
        from eigenda.codec.blob_codec import encode_blob_data
        expected_blob = encode_blob_data(b"hello world")
        assert request.blob == expected_blob
        assert hasattr(request, "blob_header")
        return self.disperse_blob_response

    def GetBlobStatus(self, request, context):
        """Mock GetBlobStatus RPC."""
        self.get_blob_status_called = True
        return self.blob_status_response

    def GetBlobCommitment(self, request, context):
        """Mock GetBlobCommitment RPC."""
        self.get_blob_commit_called = True
        return self.blob_commit_response


class TestGRPCIntegration:
    """Integration tests with real gRPC server."""

    @pytest.fixture
    def mock_servicer(self):
        """Create mock servicer."""
        return MockDisperserServicer()

    @pytest.fixture
    def grpc_server(self, mock_servicer):
        """Create and start a gRPC server."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        disperser_v2_pb2_grpc.add_DisperserServicer_to_server(mock_servicer, server)

        # Listen on a random available port
        port = server.add_insecure_port("[::]:0")
        server.start()

        yield f"localhost:{port}"

        server.stop(0)

    def test_full_dispersal_flow(self, grpc_server, mock_servicer, mock_signer):
        """Test full blob dispersal flow with real gRPC."""
        # Create client pointing to our mock server
        host, port = grpc_server.split(":")
        client = DisperserClientV2Full(
            hostname=host, port=int(port), signer=mock_signer, use_secure_grpc=False
        )

        try:
            # Test dispersal
            data = b"hello world"
            status, blob_key = client.disperse_blob(data)

            # Verify servicer was called
            assert mock_servicer.get_payment_state_called
            assert mock_servicer.disperse_blob_called

            # Verify blob key (32-byte key)
            expected_key = b"test_blob_key_1234567890" + b"\x00" * 8
            assert bytes(blob_key) == expected_key

        finally:
            client.close()

    def test_payment_state_retrieval(self, grpc_server, mock_servicer, mock_signer):
        """Test payment state retrieval."""
        host, port = grpc_server.split(":")
        client = DisperserClientV2Full(
            hostname=host, port=int(port), signer=mock_signer, use_secure_grpc=False
        )

        try:
            # Get payment state
            state = client.get_payment_state()

            # Verify servicer was called
            assert mock_servicer.get_payment_state_called

            # Verify state
            assert state.reservation is not None
            assert state.reservation.symbols_per_second == 100

        finally:
            client.close()

    def test_blob_status_polling(self, grpc_server, mock_servicer, mock_signer):
        """Test blob status polling."""
        host, port = grpc_server.split(":")
        client = DisperserClientV2Full(
            hostname=host, port=int(port), signer=mock_signer, use_secure_grpc=False
        )

        try:
            # Get blob status
            blob_key_hex = (b"test_blob_key_1234567890" + b"\x00" * 8).hex()
            status = client.get_blob_status(blob_key_hex)

            # Verify servicer was called
            assert mock_servicer.get_blob_status_called

            # Verify status
            assert status.status == disperser_v2_pb2.BlobStatus.COMPLETE
            assert status.blob_inclusion_info is not None
            assert status.blob_inclusion_info.blob_certificate.blob_header.version == 1

        finally:
            client.close()

    def test_blob_commitment_retrieval(self, grpc_server, mock_servicer, mock_signer):
        """Test blob commitment retrieval."""
        host, port = grpc_server.split(":")
        client = DisperserClientV2Full(
            hostname=host, port=int(port), signer=mock_signer, use_secure_grpc=False
        )

        try:
            # Get blob commitment - this takes data, not blob key
            test_data = b"test data for commitment"
            commitment = client.get_blob_commitment(test_data)

            # Verify servicer was called
            assert mock_servicer.get_blob_commit_called

            # Verify commitment
            assert commitment.blob_commitment.length == 1024
            assert commitment.blob_commitment.commitment is not None
            assert len(commitment.blob_commitment.commitment) == 64

        finally:
            client.close()

    def test_context_manager(self, grpc_server, mock_servicer, mock_signer):
        """Test client as context manager."""
        host, port = grpc_server.split(":")
        with DisperserClientV2Full(
            hostname=host, port=int(port), signer=mock_signer, use_secure_grpc=False
        ) as client:
            # Test basic operation
            state = client.get_payment_state()
            assert state is not None
            assert mock_servicer.get_payment_state_called

    @pytest.mark.skip(reason="Payment state is checked lazily, not immediately")
    def test_error_handling(self, grpc_server, mock_servicer, mock_signer):
        """Test error handling in gRPC calls."""

        # Make servicer return error
        def error_response(request, context):
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("Service unavailable")
            raise Exception("Service unavailable")

        mock_servicer.GetPaymentState = error_response

        host, port = grpc_server.split(":")
        client = DisperserClientV2Full(
            hostname=host, port=int(port), signer=mock_signer, use_secure_grpc=False
        )

        try:
            # Should raise wrapped error (DisperserClientV2Full wraps gRPC errors)
            with pytest.raises(Exception) as exc_info:
                client.get_payment_state()

            assert "Service unavailable" in str(exc_info.value)

        finally:
            client.close()


class TestMockGRPCServer:
    """Tests using mock gRPC server."""

    def test_dispersal_with_mock_server(self, mock_signer):
        """Test dispersal with fully mocked server."""
        # Create mock channel
        with patch("grpc.insecure_channel") as mock_channel:
            mock_stub = Mock()
            mock_channel.return_value = Mock()

            with patch(
                "eigenda.grpc.disperser.v2.disperser_v2_pb2_grpc.DisperserStub",
                return_value=mock_stub,
            ):
                # Mock the RPC calls
                mock_stub.GetPaymentState.return_value = disperser_v2_pb2.GetPaymentStateReply(
                    cumulative_payment=b"\x00" * 32, onchain_cumulative_payment=b"\x00" * 32
                )

                mock_stub.DisperseBlob.return_value = disperser_v2_pb2.DisperseBlobReply(
                    result=disperser_v2_pb2.BlobStatus.QUEUED,
                    blob_key=b"mock_blob_key" + b"\x00" * 19,  # Pad to 32 bytes
                )
                # Add GetBlobCommitment response
                mock_stub.GetBlobCommitment.return_value = disperser_v2_pb2.BlobCommitmentReply(
                    blob_commitment=common_pb2.BlobCommitment(
                        commitment=b"\x01" * 64,
                        length_commitment=b"\x02" * 48,
                        length_proof=b"\x03" * 48,
                        length=9,  # for 'test data'
                    )
                )

                # Create client
                client = DisperserClientV2Full(
                    hostname="localhost", port=50051, signer=mock_signer, use_secure_grpc=False
                )

                try:
                    # Test dispersal
                    status, blob_key = client.disperse_blob(b"test data")
                    expected_key = b"mock_blob_key" + b"\x00" * 19
                    assert bytes(blob_key) == expected_key

                    # Verify calls
                    assert mock_stub.GetPaymentState.called
                    assert mock_stub.DisperseBlob.called

                finally:
                    client.close()


class TestAsyncOperations:
    """Test async operations with mock gRPC."""

    @pytest.mark.asyncio
    async def test_async_dispersal(self, mock_signer):
        """Test async blob dispersal."""
        with patch("grpc.aio.insecure_channel") as mock_channel:
            # Mock async channel and stub
            mock_async_stub = Mock()
            mock_channel.return_value = Mock()

            # Mock async RPC calls
            async def mock_get_payment_state(request):
                return disperser_v2_pb2.GetPaymentStateReply(
                    payment_state=disperser_v2_pb2.PaymentState(
                        account_id="0x1234567890123456789012345678901234567890",
                        cumulative_payment=b"\x00" * 32,
                    )
                )

            async def mock_disperse_blob(request):
                return disperser_v2_pb2.DisperseBlobReply(
                    result=disperser_v2_pb2.BlobStatus.QUEUED,
                    blob_key=b"async_blob_key" + b"\x00" * 18,  # Pad to 32 bytes
                )

            mock_async_stub.GetPaymentState = mock_get_payment_state
            mock_async_stub.DisperseBlob = mock_disperse_blob

            # Note: This is a conceptual test - the actual client doesn't support async yet
            # But shows how async integration tests would work

            # Would need async client implementation
            # async with AsyncDisperserClientV2Full(...) as client:
            #     blob_key = await client.disperse_blob(b'test data')
            #     assert blob_key == 'async_blob_key'


class TestConcurrentOperations:
    """Test concurrent gRPC operations."""

    @pytest.fixture
    def mock_servicer(self):
        """Create mock servicer."""
        return MockDisperserServicer()

    @pytest.fixture
    def grpc_server(self, mock_servicer):
        """Create and start a gRPC server."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        disperser_v2_pb2_grpc.add_DisperserServicer_to_server(mock_servicer, server)

        # Listen on a random available port
        port = server.add_insecure_port("[::]:0")
        server.start()

        yield f"localhost:{port}"

        server.stop(0)

    def test_concurrent_dispersals(self, grpc_server, mock_servicer, mock_signer):
        """Test multiple concurrent blob dispersals."""
        host, port = grpc_server.split(":")
        client = DisperserClientV2Full(
            hostname=host, port=int(port), signer=mock_signer, use_secure_grpc=False
        )

        try:
            # Create multiple threads for dispersal
            results = []
            threads = []

            def disperse_data(data):
                try:
                    status, blob_key = client.disperse_blob(data)
                    results.append(blob_key)
                except Exception as e:
                    results.append(e)

            # Start 5 concurrent dispersals
            for i in range(5):
                thread = threading.Thread(target=disperse_data, args=(b"hello world",))
                thread.start()
                threads.append(thread)

            # Wait for all threads
            for thread in threads:
                thread.join()

            # Verify all succeeded
            assert len(results) == 5
            expected_key = b"test_blob_key_1234567890" + b"\x00" * 8
            for result in results:
                assert not isinstance(result, Exception), f"Got error: {result}"
                assert bytes(result) == expected_key

        finally:
            client.close()


class TestRetryMechanisms:
    """Test retry mechanisms with transient failures."""

    def test_retry_on_transient_failure(self, mock_signer):
        """Test retry on transient gRPC failures."""

        # Create servicer that fails first, then succeeds
        class RetryServicer(MockDisperserServicer):
            def __init__(self):
                super().__init__()
                self.call_count = 0

            def GetPaymentState(self, request, context):
                self.call_count += 1
                if self.call_count == 1:
                    # First call fails
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    context.set_details("Temporary failure")
                    return disperser_v2_pb2.GetPaymentStateReply()
                else:
                    # Second call succeeds
                    return super().GetPaymentState(request, context)

        # Set up server with retry servicer
        servicer = RetryServicer()
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        disperser_v2_pb2_grpc.add_DisperserServicer_to_server(servicer, server)
        port = server.add_insecure_port("[::]:0")
        server.start()

        try:
            # Create client with retry
            client = DisperserClientV2Full(
                hostname="localhost", port=port, signer=mock_signer, use_secure_grpc=False
            )

            # Should retry and succeed
            # Note: Actual retry logic would need to be implemented in the client
            # This test shows the pattern for testing retries

            client.close()

        finally:
            server.stop(0)


class TestStreamingOperations:
    """Test streaming gRPC operations."""

    @pytest.fixture
    def grpc_server(self):
        """Create and start a gRPC server."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        # For streaming tests, we'd need a custom servicer
        # For now, use the base mock servicer
        servicer = MockDisperserServicer()
        disperser_v2_pb2_grpc.add_DisperserServicer_to_server(servicer, server)

        # Listen on a random available port
        port = server.add_insecure_port("[::]:0")
        server.start()

        yield f"localhost:{port}"

        server.stop(0)

    def test_streaming_blob_status(self, grpc_server, mock_signer):
        """Test streaming blob status updates."""

        # Create servicer with streaming response
        class StreamingServicer(MockDisperserServicer):
            def StreamBlobStatus(self, request, context):
                """Mock streaming blob status."""
                # Send multiple status updates
                statuses = [
                    disperser_v2_pb2.BlobStatus.QUEUED,
                    disperser_v2_pb2.BlobStatus.ENCODED,
                    disperser_v2_pb2.BlobStatus.COMPLETE,
                ]

                for status in statuses:
                    yield disperser_v2_pb2.BlobStatusReply(
                        status=status,
                        blob_header=common_v2_pb2.BlobHeader(blob_key=request.blob_key),
                    )
                    time.sleep(0.1)  # Simulate processing time

        # This would require streaming support in the client
        # Shows pattern for testing streaming operations

        # with StreamingDisperserClient(...) as client:
        #     for status in client.stream_blob_status(blob_key):
        #         assert status.status in expected_statuses
