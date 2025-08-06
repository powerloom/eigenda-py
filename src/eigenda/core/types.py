"""Core type definitions for EigenDA v2."""

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import List

from eth_typing import Address

# Type aliases
BlobVersion = int
QuorumID = int


class BlobStatus(Enum):
    """Status of a dispersed blob."""

    UNKNOWN = 0
    QUEUED = 1
    ENCODED = 2
    GATHERING_SIGNATURES = 3
    COMPLETE = 4
    FAILED = 5


@dataclass
class BlobKey:
    """Unique identifier for a blob dispersal."""

    _bytes: bytes

    def __init__(self, data: bytes):
        if len(data) != 32:
            raise ValueError(f"BlobKey must be 32 bytes, got {len(data)}")
        self._bytes = data

    def hex(self) -> str:
        """Return hex representation of the blob key."""
        return self._bytes.hex()

    @classmethod
    def from_hex(cls, hex_str: str) -> "BlobKey":
        """Create BlobKey from hex string."""
        # Remove 0x prefix if present
        if hex_str.startswith(("0x", "0X")):
            hex_str = hex_str[2:]
        return cls(bytes.fromhex(hex_str))

    @classmethod
    def from_bytes(cls, data: bytes) -> "BlobKey":
        """Create BlobKey from bytes."""
        return cls(data)

    def __bytes__(self) -> bytes:
        return self._bytes

    def __repr__(self) -> str:
        return f"BlobKey({self.hex()})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BlobKey):
            return False
        return self._bytes == other._bytes


@dataclass
class G1Commitment:
    """G1 point commitment."""

    x: bytes
    y: bytes


@dataclass
class G2Commitment:
    """G2 point commitment."""

    x_a0: bytes
    x_a1: bytes
    y_a0: bytes
    y_a1: bytes


@dataclass
class BlobCommitments:
    """Blob commitments for encoding."""

    commitment: G1Commitment
    length_commitment: G2Commitment
    length_proof: G2Commitment
    length: int


@dataclass
class PaymentMetadata:
    """Payment metadata for blob dispersal."""

    account_id: Address
    cumulative_payment: int


@dataclass
class BlobHeader:
    """Metadata header for a blob."""

    blob_version: BlobVersion
    blob_commitments: BlobCommitments
    quorum_numbers: List[QuorumID]
    payment_metadata: PaymentMetadata

    def blob_key(self) -> BlobKey:
        """
        Calculate the BlobKey for this header.

        The blob key is computed as the Keccak256 hash of the serialized header
        where the payment metadata has been replaced with its hash.
        """
        # This is a simplified version - the actual implementation would need
        # to match the exact serialization format used by the Go client
        # For now, we'll create a deterministic hash
        data = (
            self.blob_version.to_bytes(2, "big")
            + self._serialize_commitments()
            + bytes(self.quorum_numbers)
            + self._hash_payment_metadata()
        )
        hash_value = hashlib.sha3_256(data).digest()
        return BlobKey(hash_value)

    def _serialize_commitments(self) -> bytes:
        """Serialize blob commitments."""
        # Simplified serialization - actual implementation needs to match Go client
        return (
            self.blob_commitments.commitment.x
            + self.blob_commitments.commitment.y
            + self.blob_commitments.length_commitment.x_a0
            + self.blob_commitments.length_commitment.x_a1
            + self.blob_commitments.length_commitment.y_a0
            + self.blob_commitments.length_commitment.y_a1
            + self.blob_commitments.length_proof.x_a0
            + self.blob_commitments.length_proof.x_a1
            + self.blob_commitments.length_proof.y_a0
            + self.blob_commitments.length_proof.y_a1
            + self.blob_commitments.length.to_bytes(4, "big")
        )

    def _hash_payment_metadata(self) -> bytes:
        """Hash the payment metadata."""
        # Simplified hashing - actual implementation needs to match Go client
        data = bytes.fromhex(
            self.payment_metadata.account_id[2:]
        ) + self.payment_metadata.cumulative_payment.to_bytes(32, "big")
        return hashlib.sha3_256(data).digest()


# Payment Types


class PaymentType(Enum):
    """Type of payment being used."""

    RESERVATION = "reservation"
    ON_DEMAND = "on_demand"
