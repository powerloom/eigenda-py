"""Blob request signing implementation."""

import hashlib

from Crypto.Hash import keccak
from eth_account import Account
from eth_typing import Address

from eigenda.utils.serialization import calculate_blob_key


class LocalBlobRequestSigner:
    """Local implementation of blob request signing using a private key."""

    def __init__(self, private_key_hex: str):
        """
        Initialize signer with a private key.

        Args:
            private_key_hex: Hex-encoded private key (with or without 0x prefix)
        """
        # Ensure private key has 0x prefix for eth_account
        if not private_key_hex.startswith("0x"):
            private_key_hex = "0x" + private_key_hex

        self.account = Account.from_key(private_key_hex)
        self.private_key = self.account.key

    def sign_blob_request(self, header) -> bytes:
        """
        Sign a blob request header.

        Args:
            header: The blob header to sign (can be protobuf or BlobHeader)

        Returns:
            The signature bytes
        """
        # Handle different header types
        if hasattr(header, "blob_key"):
            # It's our BlobHeader type
            blob_key = header.blob_key()
            key_bytes = blob_key._bytes
        else:
            # It's a protobuf header - we need to calculate the blob key
            # For v2, we sign the keccak256 hash of the serialized header
            # This matches the Go implementation
            key_bytes = self._calculate_blob_key_from_proto(header)

        # Sign the blob key directly (matching Go implementation)
        # For raw hash signing without message prefix, we use unsafe_sign_hash
        # The key_bytes should be 32 bytes (a hash)
        signature = self.account.unsafe_sign_hash(key_bytes)

        # eth_account returns v as 27 or 28, but Go expects 0 or 1
        # We need to adjust the v value
        sig_bytes = signature.signature
        r = sig_bytes[:32]
        s = sig_bytes[32:64]
        v = sig_bytes[64]

        # Adjust v from Ethereum standard (27/28) to Go standard (0/1)
        if v >= 27:
            v = v - 27

        # Return signature in the format expected by the disperser
        # (r + s + v format, 65 bytes total)
        return r + s + bytes([v])

    def _calculate_blob_key_from_proto(self, proto_header) -> bytes:
        """
        Calculate blob key from protobuf header.

        This matches the Go implementation's blob key calculation.
        """
        # Use the proper blob key calculation
        return calculate_blob_key(proto_header)

    def sign_payment_state_request(self, timestamp: int) -> bytes:
        """
        Sign a payment state request.

        Args:
            timestamp: Unix timestamp in nanoseconds

        Returns:
            The signature bytes
        """
        account_id = self.get_account_id()

        # Hash the request data (matching Go implementation)
        request_hash = self._hash_payment_state_request(account_id, timestamp)

        # Sign the hash
        signature = self.account.unsafe_sign_hash(request_hash)

        # eth_account returns v as 27 or 28, but Go expects 0 or 1
        # We need to adjust the v value
        sig_bytes = signature.signature
        r = sig_bytes[:32]
        s = sig_bytes[32:64]
        v = sig_bytes[64]

        # Adjust v from Ethereum standard (27/28) to Go standard (0/1)
        if v >= 27:
            v = v - 27

        return r + s + bytes([v])

    def get_account_id(self) -> Address:
        """
        Get the Ethereum address associated with this signer.

        Returns:
            The Ethereum address
        """
        return self.account.address

    def _hash_payment_state_request(self, account_id: Address, timestamp: int) -> bytes:
        """
        Hash a payment state request for signing.

        This matches the Go implementation in api/hashing/payment_state_hashing.go
        and Rust implementation in core/payment.rs

        Args:
            account_id: The account address
            timestamp: Unix timestamp in nanoseconds

        Returns:
            The hash to sign
        """
        # Use Keccak256 (same as sha3.NewLegacyKeccak256 in Go)
        hasher = keccak.new(digest_bits=256)

        # Hash the account ID with length prefix
        account_bytes = bytes.fromhex(account_id[2:])  # Remove 0x prefix
        # Add length prefix (4 bytes, big-endian uint32)
        hasher.update(len(account_bytes).to_bytes(4, "big"))
        hasher.update(account_bytes)

        # Hash the timestamp (8 bytes, big-endian uint64)
        hasher.update(timestamp.to_bytes(8, "big"))

        keccak_hash = hasher.digest()

        # IMPORTANT: Both Go and Rust wrap the Keccak hash with SHA256
        return hashlib.sha256(keccak_hash).digest()
