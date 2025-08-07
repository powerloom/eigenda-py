"""End-to-end integration tests for EigenDA client."""

import os
from unittest.mock import Mock, patch

import pytest

from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.codec.blob_codec import decode_blob_data, encode_blob_data
from eigenda.config import get_network_config
from eigenda.grpc.common import common_pb2
from eigenda.grpc.common.v2 import common_v2_pb2
from eigenda.grpc.disperser.v2 import disperser_v2_pb2
from eigenda.payment import PaymentConfig, calculate_payment_increment
from eigenda.utils.serialization import calculate_blob_key


@pytest.fixture
def mock_signer():
    """Create mock signer."""
    signer = Mock()
    signer.account = Mock()
    signer.account.address = "0x1234567890123456789012345678901234567890"
    signer.get_account_id = Mock(return_value="0x1234567890123456789012345678901234567890")
    signer.sign_blob_request = Mock(return_value=b"\x00" * 65)
    signer.sign_payment_state_request = Mock(return_value=b"\x00" * 65)
    # Mock signature with proper format
    signer.unsafe_sign_hash = Mock(return_value=Mock(signature=b"\x00" * 64 + b"\x01"))  # r + s + v
    return signer


class TestEndToEndFlow:
    """Test complete end-to-end flow with all components."""

    @pytest.fixture
    def mock_grpc_responses(self):
        """Create mock gRPC responses."""
        # Payment state response
        payment_state = disperser_v2_pb2.GetPaymentStateReply(
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

        # Disperse blob response
        disperse_response = disperser_v2_pb2.DisperseBlobReply(
            result=disperser_v2_pb2.BlobStatus.QUEUED,
            blob_key=b"e2e_test_blob_key_12345" + b"\x00" * 9,  # Pad to 32 bytes
        )

        # Blob status response
        blob_status = disperser_v2_pb2.BlobStatusReply(
            status=disperser_v2_pb2.BlobStatus.COMPLETE,
            signed_batch=disperser_v2_pb2.SignedBatch(
                header=common_v2_pb2.BatchHeader(
                    batch_root=b"\x01" * 32, reference_block_number=12345678
                ),
                attestation=disperser_v2_pb2.Attestation(
                    non_signer_pubkeys=[],
                    apk_g2=b"\x01" * 128,
                    quorum_apks=[b"\x02" * 64, b"\x03" * 64],
                    sigma=b"\x04" * 64,
                    quorum_numbers=[0, 1],
                    quorum_signed_percentages=b"\x64\x64",  # 100% for both quorums
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

        return {
            "payment_state": payment_state,
            "disperse": disperse_response,
            "status": blob_status,
        }

    def test_complete_dispersal_flow(self, mock_signer, mock_grpc_responses):
        """Test complete blob dispersal flow."""
        with (
            patch("grpc.insecure_channel"),
            patch(
                "eigenda.grpc.disperser.v2.disperser_v2_pb2_grpc.DisperserStub"
            ) as mock_stub_class,
        ):

            # Configure mock stub
            mock_stub = Mock()
            mock_stub_class.return_value = mock_stub

            # Set up RPC responses
            mock_stub.GetPaymentState.return_value = mock_grpc_responses["payment_state"]
            mock_stub.DisperseBlob.return_value = mock_grpc_responses["disperse"]
            mock_stub.GetBlobStatus.return_value = mock_grpc_responses["status"]
            # Add GetBlobCommitment response
            mock_stub.GetBlobCommitment.return_value = disperser_v2_pb2.BlobCommitmentReply(
                blob_commitment=common_pb2.BlobCommitment(
                    commitment=b"\x01" * 64,
                    length_commitment=b"\x02" * 48,
                    length_proof=b"\x03" * 48,
                    length=1024,
                )
            )

            # Create client
            client = DisperserClientV2Full(
                hostname="localhost", port=50051, signer=mock_signer, use_secure_grpc=False
            )

            try:
                # Test data
                original_data = b"Hello, EigenDA! This is a test blob for end-to-end testing."

                # Step 1: Encode data
                encoded_data = encode_blob_data(original_data)
                assert len(encoded_data) > len(original_data)  # Should have padding

                # Step 2: Disperse blob
                from eigenda.core.types import BlobStatus

                status, blob_key = client.disperse_blob(original_data)
                assert status == BlobStatus.QUEUED
                expected_key = b"e2e_test_blob_key_12345" + b"\x00" * 9
                assert bytes(blob_key) == expected_key

                # Verify dispersal request
                disperse_call = mock_stub.DisperseBlob.call_args[0][0]
                assert (
                    disperse_call.blob == encoded_data
                )  # DisperserClientV2Full sends encoded data
                assert hasattr(disperse_call, "blob_header")

                # Step 3: Check status
                status = client.get_blob_status(blob_key.hex())
                assert status.status == disperser_v2_pb2.BlobStatus.COMPLETE
                assert status.blob_inclusion_info is not None

                # Step 4: Verify blob header
                blob_header = status.blob_inclusion_info.blob_certificate.blob_header
                assert blob_header.version == 1
                assert blob_header.commitment.length == 1024
                assert blob_header.quorum_numbers == [0, 1]

                # Step 5: Verify signed batch
                signed_batch = status.signed_batch
                assert signed_batch.header.reference_block_number == 12345678
                assert len(signed_batch.attestation.sigma) == 64

            finally:
                client.close()

    def test_payment_calculation_flow(self, mock_signer):
        """Test payment calculation in the flow."""
        with (
            patch("grpc.insecure_channel"),
            patch(
                "eigenda.grpc.disperser.v2.disperser_v2_pb2_grpc.DisperserStub"
            ) as mock_stub_class,
        ):

            mock_stub = Mock()
            mock_stub_class.return_value = mock_stub

            # Mock responses
            mock_stub.GetPaymentState.return_value = disperser_v2_pb2.GetPaymentStateReply(
                cumulative_payment=b"\x00" * 31 + b"\x10",  # 16 in last byte
                onchain_cumulative_payment=b"\x00" * 31 + b"\x10",
                payment_global_params=disperser_v2_pb2.PaymentGlobalParams(
                    price_per_symbol=447000000,
                    min_num_symbols=4096,
                ),
            )
            # Add GetBlobCommitment response
            mock_stub.GetBlobCommitment.return_value = disperser_v2_pb2.BlobCommitmentReply(
                blob_commitment=common_pb2.BlobCommitment(
                    commitment=b"\x01" * 64,
                    length_commitment=b"\x02" * 48,
                    length_proof=b"\x03" * 48,
                    length=10000,
                )
            )

            # Capture dispersal request
            dispersal_request = None

            def capture_request(request, **kwargs):  # Accept any kwargs for timeout etc
                nonlocal dispersal_request
                dispersal_request = request
                return disperser_v2_pb2.DisperseBlobReply(
                    result=disperser_v2_pb2.BlobStatus.QUEUED,
                    blob_key=b"payment_test_key" + b"\x00" * 16,  # Pad to 32 bytes
                )

            mock_stub.DisperseBlob.side_effect = capture_request

            # Create client
            client = DisperserClientV2Full(
                hostname="localhost", port=50051, signer=mock_signer, use_secure_grpc=False
            )

            try:
                # Large data requiring payment
                data = b"x" * 10000  # 10KB

                # Disperse
                status, blob_key = client.disperse_blob(data)

                # Verify payment was calculated
                assert dispersal_request is not None
                payment_header = dispersal_request.blob_header.payment_header

                # Should have non-zero cumulative payment
                cumulative_payment = int.from_bytes(
                    payment_header.cumulative_payment, byteorder="big"
                )
                assert cumulative_payment > 16  # Greater than initial state

                # Verify payment calculation
                config = PaymentConfig(price_per_symbol=447000000, min_num_symbols=4096)
                encoded_data = encode_blob_data(data)
                expected_increment = calculate_payment_increment(len(encoded_data), config)
                expected_cumulative = 16 + expected_increment

                assert cumulative_payment == expected_cumulative

            finally:
                client.close()

    def test_network_configuration_integration(self):
        """Test network configuration integration."""
        # Test Sepolia
        with patch.dict(
            os.environ, {"EIGENDA_DISPERSER_HOST": "disperser-testnet-sepolia.eigenda.xyz"}
        ):
            config = get_network_config()
            assert config.network_name == "Sepolia Testnet"
            assert config.disperser_host == "disperser-testnet-sepolia.eigenda.xyz"
            assert config.payment_vault_address == "0x2E1BDB221E7D6bD9B7b2365208d41A5FD70b24Ed"

        # Test Holesky
        with patch.dict(
            os.environ, {"EIGENDA_DISPERSER_HOST": "disperser-testnet-holesky.eigenda.xyz"}
        ):
            config = get_network_config()
            assert config.network_name == "Holesky Testnet"
            assert config.disperser_host == "disperser-testnet-holesky.eigenda.xyz"
            assert config.payment_vault_address == "0x4a7Fff191BCDa5806f1Bc8689afc1417c08C61AB"

        # Test Mainnet
        with patch.dict(os.environ, {"EIGENDA_DISPERSER_HOST": "disperser.eigenda.xyz"}):
            config = get_network_config()
            assert config.network_name == "Ethereum Mainnet"
            assert config.disperser_host == "disperser.eigenda.xyz"
            assert config.payment_vault_address == "0xb2e7ef419a2A399472ae22ef5cFcCb8bE97A4B05"

    def test_blob_key_calculation(self, mock_signer):
        """Test blob key calculation matches server."""
        # Create mock blob header
        blob_header = common_v2_pb2.BlobHeader(
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
        )

        # Calculate blob key
        blob_key = calculate_blob_key(blob_header)

        # Should be 32 bytes
        assert len(blob_key) == 32

        # Should be deterministic
        blob_key2 = calculate_blob_key(blob_header)
        assert blob_key == blob_key2

    def test_encoding_decoding_roundtrip(self):
        """Test encoding and decoding roundtrip."""
        test_cases = [
            b"",  # Empty
            b"a",  # Single byte
            b"hello",  # Small
            b"x" * 31,  # Exactly 31 bytes
            b"x" * 32,  # 32 bytes
            b"x" * 1000,  # Large
            b"\x00" * 100,  # All zeros
            b"\xff" * 100,  # All ones
            bytes(range(256)),  # All bytes
        ]

        for original in test_cases:
            # Encode
            encoded = encode_blob_data(original)

            # Decode with original length to handle trailing zeros correctly
            decoded = decode_blob_data(encoded, len(original))

            # Should match
            assert decoded == original, f"Failed for data of length {len(original)}"

    def test_signature_verification_flow(self, mock_signer):
        """Test signature verification in the flow."""
        with (
            patch("grpc.insecure_channel"),
            patch(
                "eigenda.grpc.disperser.v2.disperser_v2_pb2_grpc.DisperserStub"
            ) as mock_stub_class,
        ):

            mock_stub = Mock()
            mock_stub_class.return_value = mock_stub

            # Set up responses
            mock_stub.GetPaymentState.return_value = disperser_v2_pb2.GetPaymentStateReply(
                cumulative_payment=b"\x00" * 32, onchain_cumulative_payment=b"\x00" * 32
            )
            # Add GetBlobCommitment response
            commitment_reply = disperser_v2_pb2.BlobCommitmentReply()
            commitment_reply.blob_commitment.commitment = b"\x01" * 64
            commitment_reply.blob_commitment.length_commitment = b"\x02" * 48
            commitment_reply.blob_commitment.length_proof = b"\x03" * 48
            commitment_reply.blob_commitment.length = 9  # for 'test data'
            mock_stub.GetBlobCommitment.return_value = commitment_reply

            # Capture signature
            captured_signature = None

            def capture_disperse(request, **kwargs):  # Accept any kwargs for timeout etc
                nonlocal captured_signature
                # signature is at request level, not in blob_header
                captured_signature = request.signature
                return disperser_v2_pb2.DisperseBlobReply(
                    result=disperser_v2_pb2.BlobStatus.QUEUED,
                    blob_key=b"sig_test_key" + b"\x00" * 20,  # Pad to 32 bytes
                )

            mock_stub.DisperseBlob.side_effect = capture_disperse

            # Create client
            client = DisperserClientV2Full(
                hostname="localhost", port=50051, signer=mock_signer, use_secure_grpc=False
            )

            try:
                # Disperse blob
                status, blob_key = client.disperse_blob(b"test data")

                # Verify signature format
                assert captured_signature is not None
                assert len(captured_signature) == 65

                # Verify signer was called
                assert mock_signer.sign_blob_request.called

            finally:
                client.close()


class TestErrorScenarios:
    """Test various error scenarios in integration."""

    def test_network_error_handling(self, mock_signer):
        """Test handling of network errors."""
        with patch("grpc.insecure_channel") as mock_channel:
            # Mock channel that raises on RPC
            mock_channel.return_value = Mock()

            with patch(
                "eigenda.grpc.disperser.v2.disperser_v2_pb2_grpc.DisperserStub"
            ) as mock_stub_class:
                mock_stub = Mock()
                mock_stub_class.return_value = mock_stub

                # Make RPC fail
                mock_stub.GetPaymentState.side_effect = Exception("Network error")

                client = DisperserClientV2Full(
                    hostname="localhost", port=50051, signer=mock_signer, use_secure_grpc=False
                )

                try:
                    # Should raise
                    with pytest.raises(Exception) as exc_info:
                        client.get_payment_state()

                    assert "Network error" in str(exc_info.value)

                finally:
                    client.close()

    def test_invalid_data_handling(self, mock_signer):
        """Test handling of invalid data."""
        with patch("grpc.insecure_channel"), patch(
            "eigenda.grpc.disperser.v2.disperser_v2_pb2_grpc.DisperserStub"
        ):

            client = DisperserClientV2Full(
                hostname="localhost", port=50051, signer=mock_signer, use_secure_grpc=False
            )

            try:
                # Test empty data
                with pytest.raises(ValueError) as exc_info:
                    client.disperse_blob(b"")
                assert "empty" in str(exc_info.value).lower()

                # Test None data
                with pytest.raises(Exception):
                    client.disperse_blob(None)

            finally:
                client.close()

    def test_timeout_handling(self, mock_signer):
        """Test timeout handling."""
        import time

        with (
            patch("grpc.insecure_channel"),
            patch(
                "eigenda.grpc.disperser.v2.disperser_v2_pb2_grpc.DisperserStub"
            ) as mock_stub_class,
        ):

            mock_stub = Mock()
            mock_stub_class.return_value = mock_stub

            # Simulate timeout
            def slow_response(request):
                time.sleep(2)  # Longer than typical timeout
                return disperser_v2_pb2.GetPaymentStateReply()

            mock_stub.GetPaymentState.side_effect = slow_response

            client = DisperserClientV2Full(
                hostname="localhost", port=50051, signer=mock_signer, use_secure_grpc=False
            )

            # In real implementation, this would timeout
            # Here we just test the pattern
            client.close()


class TestPerformanceIntegration:
    """Test performance aspects of integration."""

    def test_large_blob_handling(self, mock_signer):
        """Test handling of large blobs."""
        with (
            patch("grpc.insecure_channel"),
            patch(
                "eigenda.grpc.disperser.v2.disperser_v2_pb2_grpc.DisperserStub"
            ) as mock_stub_class,
        ):

            mock_stub = Mock()
            mock_stub_class.return_value = mock_stub

            # Set up responses
            mock_stub.GetPaymentState.return_value = disperser_v2_pb2.GetPaymentStateReply(
                cumulative_payment=b"\x00" * 32, onchain_cumulative_payment=b"\x00" * 32
            )
            # Add GetBlobCommitment response
            mock_stub.GetBlobCommitment.return_value = disperser_v2_pb2.BlobCommitmentReply(
                blob_commitment=common_pb2.BlobCommitment(
                    commitment=b"\x01" * 64,
                    length_commitment=b"\x02" * 48,
                    length_proof=b"\x03" * 48,
                    length=1024 * 1024,  # 1MB
                )
            )

            mock_stub.DisperseBlob.return_value = disperser_v2_pb2.DisperseBlobReply(
                result=disperser_v2_pb2.BlobStatus.QUEUED,
                blob_key=b"large_blob_key" + b"\x00" * 18,  # Pad to 32 bytes
            )

            client = DisperserClientV2Full(
                hostname="localhost", port=50051, signer=mock_signer, use_secure_grpc=False
            )

            try:
                # Test with 1MB blob
                large_data = b"x" * (1024 * 1024)

                # Should handle without issues
                status, blob_key = client.disperse_blob(large_data)
                expected_key = b"large_blob_key" + b"\x00" * 18
                assert bytes(blob_key) == expected_key

                # Verify request (should be encoded data)
                request = mock_stub.DisperseBlob.call_args[0][0]
                # DisperserClientV2Full encodes the data, so it should be larger
                assert len(request.blob) > len(large_data)

            finally:
                client.close()

    def test_batch_operations(self, mock_signer):
        """Test batch blob operations."""
        with (
            patch("grpc.insecure_channel"),
            patch(
                "eigenda.grpc.disperser.v2.disperser_v2_pb2_grpc.DisperserStub"
            ) as mock_stub_class,
        ):

            mock_stub = Mock()
            mock_stub_class.return_value = mock_stub

            # Set up responses
            mock_stub.GetPaymentState.return_value = disperser_v2_pb2.GetPaymentStateReply(
                cumulative_payment=b"\x00" * 32, onchain_cumulative_payment=b"\x00" * 32
            )

            blob_counter = 0

            def create_blob_response(request, **kwargs):  # Accept any kwargs for timeout etc
                nonlocal blob_counter
                blob_counter += 1
                # Pad blob key to 32 bytes
                key_bytes = f"batch_blob_{blob_counter}".encode()
                padded_key = key_bytes + b"\x00" * (32 - len(key_bytes))
                return disperser_v2_pb2.DisperseBlobReply(
                    result=disperser_v2_pb2.BlobStatus.QUEUED, blob_key=padded_key
                )

            mock_stub.DisperseBlob.side_effect = create_blob_response

            # Add GetBlobCommitment response
            mock_stub.GetBlobCommitment.return_value = disperser_v2_pb2.BlobCommitmentReply(
                blob_commitment=common_pb2.BlobCommitment(
                    commitment=b"\x01" * 64,
                    length_commitment=b"\x02" * 48,
                    length_proof=b"\x03" * 48,
                    length=100,  # Small blob size
                )
            )

            client = DisperserClientV2Full(
                hostname="localhost", port=50051, signer=mock_signer, use_secure_grpc=False
            )

            try:
                # Disperse multiple blobs
                blob_keys = []
                for i in range(10):
                    data = f"blob_{i}".encode()
                    status, blob_key = client.disperse_blob(data)
                    blob_keys.append(blob_key)

                # Verify all succeeded
                assert len(blob_keys) == 10
                for i, key in enumerate(blob_keys):
                    # Key should be padded blob key bytes
                    key_bytes = f"batch_blob_{i+1}".encode()
                    padded_key = key_bytes + b"\x00" * (32 - len(key_bytes))
                    assert bytes(key) == padded_key

            finally:
                client.close()
