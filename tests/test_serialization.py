"""Tests for serialization and blob key calculation."""

from eigenda.utils.abi_encoding import (
    calculate_blob_key,
    encode_blob_commitments,
    encode_blob_commitments_tuple,
    hash_payment_metadata,
)


# Mock classes for testing
class MockPaymentHeader:
    def __init__(self, account_id, timestamp, cumulative_payment):
        self.account_id = account_id
        self.timestamp = timestamp
        self.cumulative_payment = cumulative_payment


class MockBlobCommitment:
    def __init__(self, commitment, length_commitment, length_proof, length):
        self.commitment = commitment
        self.length_commitment = length_commitment
        self.length_proof = length_proof
        self.length = length


class MockBlobHeader:
    def __init__(self, version, quorum_numbers, commitment, payment_header):
        self.version = version
        self.quorum_numbers = quorum_numbers
        self.commitment = commitment
        self.payment_header = payment_header


class TestPaymentMetadataHashing:
    """Test payment metadata hashing functionality."""

    def test_hash_payment_metadata_with_0x_prefix(self):
        """Test hashing payment metadata with 0x prefix."""
        payment_header = MockPaymentHeader(
            account_id="0x1234567890123456789012345678901234567890",
            timestamp=1234567890,
            cumulative_payment=b"\x00\x01\x02\x03\x04\x05\x06\x07",
        )

        hash_result = hash_payment_metadata(payment_header)

        # Should be 32 bytes
        assert len(hash_result) == 32
        assert isinstance(hash_result, bytes)

    def test_hash_payment_metadata_without_0x_prefix(self):
        """Test hashing payment metadata without 0x prefix."""
        payment_header = MockPaymentHeader(
            account_id="1234567890123456789012345678901234567890",
            timestamp=1234567890,
            cumulative_payment=b"\x00\x01\x02\x03\x04\x05\x06\x07",
        )

        hash_result = hash_payment_metadata(payment_header)

        # Should be 32 bytes
        assert len(hash_result) == 32
        assert isinstance(hash_result, bytes)

    def test_hash_payment_metadata_empty_payment(self):
        """Test hashing with empty cumulative payment (reservation mode)."""
        payment_header = MockPaymentHeader(
            account_id="0x1234567890123456789012345678901234567890",
            timestamp=1234567890,
            cumulative_payment=b"",  # Empty means 0
        )

        hash_result = hash_payment_metadata(payment_header)

        # Should be 32 bytes
        assert len(hash_result) == 32
        assert isinstance(hash_result, bytes)

    def test_hash_payment_metadata_large_payment(self):
        """Test hashing with large cumulative payment."""
        # 1 ETH in wei
        one_eth = (10**18).to_bytes(32, byteorder="big")

        payment_header = MockPaymentHeader(
            account_id="0x1234567890123456789012345678901234567890",
            timestamp=1234567890,
            cumulative_payment=one_eth,
        )

        hash_result = hash_payment_metadata(payment_header)

        # Should be 32 bytes
        assert len(hash_result) == 32
        assert isinstance(hash_result, bytes)

    def test_hash_payment_metadata_consistency(self):
        """Test that hashing is consistent."""
        payment_header = MockPaymentHeader(
            account_id="0x1234567890123456789012345678901234567890",
            timestamp=1234567890,
            cumulative_payment=b"\x00\x01\x02\x03\x04\x05\x06\x07",
        )

        hash1 = hash_payment_metadata(payment_header)
        hash2 = hash_payment_metadata(payment_header)

        assert hash1 == hash2


class TestBlobCommitmentsEncoding:
    """Test blob commitments ABI encoding."""

    def test_encode_blob_commitments_v2(self):
        """Test encoding v2 blob commitments with G1/G2 points."""

        # Create a mock v2 blob commitment with direct G1/G2 points
        class MockG1Point:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class MockG2Point:
            def __init__(self, x_a0, x_a1, y_a0, y_a1):
                self.x_a0 = x_a0
                self.x_a1 = x_a1
                self.y_a0 = y_a0
                self.y_a1 = y_a1

        class MockBlobCommitmentV2:
            def __init__(self):
                self.commitment = MockG1Point(
                    b"\x00" * 31 + b"\x01", b"\x00" * 31 + b"\x02"  # x = 1  # y = 2
                )
                self.length_commitment = MockG2Point(
                    b"\x00" * 31 + b"\x03",  # x_a0 = 3
                    b"\x00" * 31 + b"\x04",  # x_a1 = 4
                    b"\x00" * 31 + b"\x05",  # y_a0 = 5
                    b"\x00" * 31 + b"\x06",  # y_a1 = 6
                )
                self.length_proof = MockG2Point(
                    b"\x00" * 31 + b"\x07",  # x_a0 = 7
                    b"\x00" * 31 + b"\x08",  # x_a1 = 8
                    b"\x00" * 31 + b"\x09",  # y_a0 = 9
                    b"\x00" * 31 + b"\x0a",  # y_a1 = 10
                )
                self.data_length = 1024

        commitment = MockBlobCommitmentV2()
        encoded = encode_blob_commitments(commitment)

        # Should produce valid ABI encoded bytes
        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

    def test_encode_blob_commitments_tuple_compressed_g1(self):
        """Test encoding tuple with compressed G1 point."""
        # Create a v1 blob commitment with compressed G1 point
        # Use a valid non-zero x coordinate (1)
        commitment = MockBlobCommitment(
            commitment=b"\x80" + b"\x00" * 30 + b"\x01",  # Compressed G1 point with x=1
            length_commitment=b"\x00" * 64,  # Compressed G2 point
            length_proof=b"\x00" * 64,  # Compressed G2 point
            length=1024,
        )

        # This should use the decompression logic and work correctly
        result = encode_blob_commitments_tuple(commitment)

        assert isinstance(result, tuple)
        assert len(result) == 5
        # Check that x coordinate is 1
        assert result[0] == 1
        # y should be non-zero
        assert result[1] != 0

    def test_encode_blob_commitments_tuple_uncompressed(self):
        """Test encoding tuple with uncompressed points."""
        # Create a v1 blob commitment with uncompressed points
        commitment = MockBlobCommitment(
            commitment=b"\x00" * 32 + b"\x01" * 32,  # Uncompressed G1 (64 bytes)
            length_commitment=b"\x00" * 128,  # Uncompressed G2 (128 bytes)
            length_proof=b"\x00" * 128,  # Uncompressed G2 (128 bytes)
            length=1024,
        )

        # This should work without decompression
        result = encode_blob_commitments_tuple(commitment)

        assert isinstance(result, tuple)
        assert len(result) == 5
        # Check G1 point
        assert result[0] == 0  # x coordinate
        assert result[1] == int.from_bytes(b"\x01" * 32, "big")  # y coordinate
        # Check G2 points are tuples with Ethereum ordering (A1, A0)
        assert isinstance(result[2], tuple)
        assert isinstance(result[3], tuple)
        assert result[4] == 1024


class TestBlobKeyCalculation:
    """Test blob key calculation."""

    def test_calculate_blob_key_basic(self):
        """Test basic blob key calculation."""
        # Create a mock blob header with uncompressed points
        commitment = MockBlobCommitment(
            commitment=b"\x00" * 32 + b"\x01" * 32,  # Uncompressed G1
            length_commitment=b"\x00" * 128,  # Uncompressed G2
            length_proof=b"\x00" * 128,  # Uncompressed G2
            length=1024,
        )

        payment_header = MockPaymentHeader(
            account_id="0x1234567890123456789012345678901234567890",
            timestamp=1234567890,
            cumulative_payment=b"\x00\x01\x02\x03\x04\x05\x06\x07",
        )

        blob_header = MockBlobHeader(
            version=1,
            quorum_numbers=[0, 1, 2],
            commitment=commitment,
            payment_header=payment_header,
        )

        blob_key = calculate_blob_key(blob_header)

        # Should be 32 bytes
        assert len(blob_key) == 32
        assert isinstance(blob_key, bytes)

    def test_calculate_blob_key_quorum_sorting(self):
        """Test that quorum numbers are sorted."""
        commitment = MockBlobCommitment(
            commitment=b"\x00" * 64,  # Uncompressed G1
            length_commitment=b"\x00" * 128,  # Uncompressed G2
            length_proof=b"\x00" * 128,  # Uncompressed G2
            length=1024,
        )

        payment_header = MockPaymentHeader(
            account_id="0x1234567890123456789012345678901234567890",
            timestamp=1234567890,
            cumulative_payment=b"",
        )

        # Create headers with different quorum orders
        blob_header1 = MockBlobHeader(
            version=1,
            quorum_numbers=[2, 0, 1],  # Unsorted
            commitment=commitment,
            payment_header=payment_header,
        )

        blob_header2 = MockBlobHeader(
            version=1,
            quorum_numbers=[0, 1, 2],  # Already sorted
            commitment=commitment,
            payment_header=payment_header,
        )

        # Both should produce the same blob key
        key1 = calculate_blob_key(blob_header1)
        key2 = calculate_blob_key(blob_header2)

        assert key1 == key2

    def test_calculate_blob_key_different_versions(self):
        """Test blob key calculation with different versions."""
        commitment = MockBlobCommitment(
            commitment=b"\x00" * 64,
            length_commitment=b"\x00" * 128,
            length_proof=b"\x00" * 128,
            length=1024,
        )

        payment_header = MockPaymentHeader(
            account_id="0x1234567890123456789012345678901234567890",
            timestamp=1234567890,
            cumulative_payment=b"",
        )

        blob_header_v1 = MockBlobHeader(
            version=1, quorum_numbers=[0, 1], commitment=commitment, payment_header=payment_header
        )

        blob_header_v2 = MockBlobHeader(
            version=2, quorum_numbers=[0, 1], commitment=commitment, payment_header=payment_header
        )

        key1 = calculate_blob_key(blob_header_v1)
        key2 = calculate_blob_key(blob_header_v2)

        # Different versions should produce different keys
        assert key1 != key2

    def test_calculate_blob_key_consistency(self):
        """Test that blob key calculation is consistent."""
        commitment = MockBlobCommitment(
            commitment=b"\x00" * 64,
            length_commitment=b"\x00" * 128,
            length_proof=b"\x00" * 128,
            length=1024,
        )

        payment_header = MockPaymentHeader(
            account_id="0x1234567890123456789012345678901234567890",
            timestamp=1234567890,
            cumulative_payment=b"\x00\x01\x02\x03\x04\x05\x06\x07",
        )

        blob_header = MockBlobHeader(
            version=1,
            quorum_numbers=[0, 1, 2],
            commitment=commitment,
            payment_header=payment_header,
        )

        # Calculate multiple times
        key1 = calculate_blob_key(blob_header)
        key2 = calculate_blob_key(blob_header)
        key3 = calculate_blob_key(blob_header)

        # All should be the same
        assert key1 == key2 == key3
