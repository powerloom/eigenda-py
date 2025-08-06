"""ABI encoding utilities for EigenDA v2."""

from typing import Any, Tuple

from eth_abi import encode
from eth_utils import keccak


def encode_blob_commitments(commitment: Any) -> bytes:
    """
    ABI encode blob commitments matching the Go/Rust implementation.

    The structure is:
    - commitment: (uint256 X, uint256 Y)
    - lengthCommitment: (uint256[2] X, uint256[2] Y)
    - lengthProof: (uint256[2] X, uint256[2] Y)
    - dataLength: uint32

    Args:
        commitment: The protobuf BlobCommitment

    Returns:
        ABI encoded bytes
    """
    # Extract G1 point (commitment)
    commitment_x = int.from_bytes(commitment.commitment.x, byteorder="big")
    commitment_y = int.from_bytes(commitment.commitment.y, byteorder="big")

    # Extract G2 points (length_commitment and length_proof)
    # G2 points in Ethereum use (A1, A0) ordering instead of (A0, A1)
    length_commitment_x = [
        int.from_bytes(commitment.length_commitment.x_a1, byteorder="big"),
        int.from_bytes(commitment.length_commitment.x_a0, byteorder="big"),
    ]
    length_commitment_y = [
        int.from_bytes(commitment.length_commitment.y_a1, byteorder="big"),
        int.from_bytes(commitment.length_commitment.y_a0, byteorder="big"),
    ]

    length_proof_x = [
        int.from_bytes(commitment.length_proof.x_a1, byteorder="big"),
        int.from_bytes(commitment.length_proof.x_a0, byteorder="big"),
    ]
    length_proof_y = [
        int.from_bytes(commitment.length_proof.y_a1, byteorder="big"),
        int.from_bytes(commitment.length_proof.y_a0, byteorder="big"),
    ]

    # Encode the entire commitments struct
    # This matches the abiBlobCommitments struct in Go
    encoded = encode(
        ["(uint256,uint256,(uint256[2],uint256[2]),(uint256[2],uint256[2]),uint32)"],
        [
            (
                commitment_x,
                commitment_y,
                (length_commitment_x, length_commitment_y),
                (length_proof_x, length_proof_y),
                commitment.data_length,
            )
        ],
    )

    return encoded


def calculate_blob_key(blob_header: Any) -> bytes:
    """
    Calculate the blob key matching the Go/Rust implementation exactly.

    The blob key is computed as:
    1. First hash = keccak256(abi.encode(version, sortedQuorumNumbers, blobCommitments))
    2. Final key = keccak256(abi.encode(firstHash, paymentMetadataHash))

    Args:
        blob_header: Protobuf BlobHeader

    Returns:
        32-byte blob key
    """
    # Sort quorum numbers
    sorted_quorums = sorted(blob_header.quorum_numbers)
    quorum_bytes = bytes(sorted_quorums)

    # First, encode version, quorum numbers, and commitments
    header_encoded = encode(
        [
            "uint16",
            "bytes",
            "(uint256,uint256,(uint256[2],uint256[2]),(uint256[2],uint256[2]),uint32)",
        ],
        [blob_header.version, quorum_bytes, encode_blob_commitments_tuple(blob_header.commitment)],
    )

    # Hash the header
    header_hash = keccak(header_encoded)

    # Calculate payment metadata hash
    payment_hash = hash_payment_metadata(blob_header.payment_header)

    # Second encoding: header hash + payment metadata hash
    # This is encoded as a tuple per the Go implementation
    final_encoded = encode(["(bytes32,bytes32)"], [(header_hash, payment_hash)])

    # Final hash to get blob key
    blob_key = keccak(final_encoded)

    return blob_key


def encode_blob_commitments_tuple(commitment: Any) -> Tuple:
    """
    Convert protobuf BlobCommitment to a tuple for ABI encoding.

    Args:
        commitment: Protobuf BlobCommitment (v1 format with serialized bytes)

    Returns:
        Tuple suitable for ABI encoding
    """
    # The v1 BlobCommitment has these fields as raw bytes:
    # - commitment: 64 bytes (x: 32, y: 32)
    # - length_commitment: 128 bytes (G2 point)
    # - length_proof: 128 bytes (G2 point)
    # - length: uint32

    # Extract G1 point (commitment)
    # The commitment field is in gnark-crypto compressed format
    commitment_bytes = commitment.commitment
    if len(commitment_bytes) == 32:
        # Import our gnark decompression utilities
        from .gnark_decompression import decompress_g1_point_gnark

        # Decompress the G1 point
        commitment_x, commitment_y = decompress_g1_point_gnark(commitment_bytes)
    else:
        # If somehow we get uncompressed format (64 bytes)
        commitment_x = int.from_bytes(commitment_bytes[:32], byteorder="big")
        commitment_y = int.from_bytes(commitment_bytes[32:64], byteorder="big")

    # Extract G2 points with Ethereum ordering (A1, A0)
    # The disperser sends compressed G2 points (64 bytes each)
    from .gnark_decompression import decompress_g2_point_gnark

    length_commitment_bytes = commitment.length_commitment
    length_proof_bytes = commitment.length_proof

    if len(length_commitment_bytes) == 64:
        # Compressed G2 format
        (lc_x_a0, lc_x_a1), (lc_y_a0, lc_y_a1) = decompress_g2_point_gnark(length_commitment_bytes)
    else:
        # Full 128 bytes with X and Y
        lc_x_a0 = int.from_bytes(length_commitment_bytes[0:32], byteorder="big")
        lc_x_a1 = int.from_bytes(length_commitment_bytes[32:64], byteorder="big")
        lc_y_a0 = int.from_bytes(length_commitment_bytes[64:96], byteorder="big")
        lc_y_a1 = int.from_bytes(length_commitment_bytes[96:128], byteorder="big")

    if len(length_proof_bytes) == 64:
        # Compressed G2 format
        (lp_x_a0, lp_x_a1), (lp_y_a0, lp_y_a1) = decompress_g2_point_gnark(length_proof_bytes)
    else:
        # Full 128 bytes with X and Y
        lp_x_a0 = int.from_bytes(length_proof_bytes[0:32], byteorder="big")
        lp_x_a1 = int.from_bytes(length_proof_bytes[32:64], byteorder="big")
        lp_y_a0 = int.from_bytes(length_proof_bytes[64:96], byteorder="big")
        lp_y_a1 = int.from_bytes(length_proof_bytes[96:128], byteorder="big")

    # Return in Ethereum ordering (A1, A0)
    return (
        commitment_x,
        commitment_y,
        ([lc_x_a1, lc_x_a0], [lc_y_a1, lc_y_a0]),
        ([lp_x_a1, lp_x_a0], [lp_y_a1, lp_y_a0]),
        commitment.length,
    )


def hash_payment_metadata(payment_header: Any) -> bytes:
    """
    Hash payment metadata according to the protocol.

    The payment metadata is ABI encoded as a tuple with:
    - account_id (string) - hex string with 0x prefix
    - timestamp (int64) - nanosecond timestamp
    - cumulative_payment (uint256) - big integer

    Args:
        payment_header: Protobuf PaymentHeader

    Returns:
        32-byte hash
    """
    # Ensure account_id has 0x prefix
    account_id = payment_header.account_id
    if not account_id.startswith("0x"):
        account_id = "0x" + account_id

    # Convert cumulative_payment from bytes to int
    # Empty bytes means 0 (reservation-based payment)
    if len(payment_header.cumulative_payment) == 0:
        cumulative_payment = 0
    else:
        cumulative_payment = int.from_bytes(payment_header.cumulative_payment, byteorder="big")

    # ABI encode as tuple matching Go implementation
    encoded = encode(
        ["(string,int64,uint256)"], [(account_id, payment_header.timestamp, cumulative_payment)]
    )

    return keccak(encoded)
