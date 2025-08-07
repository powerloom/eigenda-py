"""EigenDA v2 Disperser Client implementation."""

import hashlib
import struct
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import grpc

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.core.types import BlobKey, BlobStatus, BlobVersion, QuorumID


@dataclass
class DisperserClientConfig:
    """Configuration for the disperser client."""

    hostname: str
    port: int
    use_secure_grpc: bool = True
    timeout: int = 30


class DisperserClient:
    """Client for interacting with the EigenDA v2 Disperser service."""

    def __init__(
        self,
        hostname: str,
        port: int,
        use_secure_grpc: bool,
        signer: LocalBlobRequestSigner,
        config: Optional[DisperserClientConfig] = None,
    ):
        """
        Initialize the disperser client.

        Args:
            hostname: Disperser service hostname
            port: Disperser service port
            use_secure_grpc: Whether to use TLS
            signer: Request signer for authentication
            config: Optional additional configuration
        """
        self.hostname = hostname
        self.port = port
        self.use_secure_grpc = use_secure_grpc
        self.signer = signer
        self.config = config or DisperserClientConfig(
            hostname=hostname, port=port, use_secure_grpc=use_secure_grpc
        )

        self._channel: Optional[grpc.Channel] = None
        self._connected = False

    def _connect(self):
        """Establish gRPC connection."""
        if self._connected:
            return

        target = f"{self.hostname}:{self.port}"

        if self.use_secure_grpc:
            credentials = grpc.ssl_channel_credentials()
            self._channel = grpc.secure_channel(target, credentials)
        else:
            self._channel = grpc.insecure_channel(target)

        self._connected = True

    def disperse_blob(
        self,
        data: bytes,
        blob_version: BlobVersion,
        quorum_numbers: List[QuorumID],
        timeout: Optional[int] = None,
    ) -> Tuple[BlobStatus, BlobKey]:
        """
        Disperse a blob to the EigenDA network.

        Args:
            data: The encoded blob data to disperse
            blob_version: Version of the blob format
            quorum_numbers: List of quorum IDs to disperse to
            timeout: Optional timeout in seconds

        Returns:
            Tuple of (status, blob_key)
        """
        # For now, we'll implement a simplified version that demonstrates the structure
        # In a full implementation, this would use the generated gRPC stubs

        self._connect()

        # Validate data
        if len(data) == 0:
            raise ValueError("Data cannot be empty")
        if len(data) > 16 * 1024 * 1024:  # 16 MiB limit
            raise ValueError("Data exceeds maximum size of 16 MiB")

        # Create a mock blob header (in real implementation, this would be properly constructed)
        # For demonstration purposes, we'll create a simplified version
        blob_key = self._calculate_blob_key(data, blob_version, quorum_numbers)

        # In a real implementation, we would:
        # 1. Create a proper BlobHeader with commitments
        # 2. Sign the header
        # 3. Send the DisperseBlobRequest via gRPC
        # 4. Parse the response

        # For now, return mock values
        return (BlobStatus.QUEUED, blob_key)

    def get_blob_status(self, blob_key: BlobKey) -> BlobStatus:
        """
        Get the status of a dispersed blob.

        Args:
            blob_key: The unique identifier of the blob

        Returns:
            The current status of the blob
        """
        self._connect()

        # In a real implementation, this would make a gRPC call
        # For now, return a mock status
        return BlobStatus.COMPLETE

    def close(self):
        """Close the gRPC connection."""
        if self._channel:
            self._channel.close()
            self._connected = False
            self._channel = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _calculate_blob_key(
        self, data: bytes, blob_version: BlobVersion, quorum_numbers: List[QuorumID]
    ) -> BlobKey:
        """
        Calculate a mock blob key for demonstration.

        In a real implementation, this would use the actual blob header
        and proper serialization.
        """
        # Create a deterministic hash based on the inputs
        hasher = hashlib.sha3_256()
        hasher.update(struct.pack(">H", blob_version))  # 2 bytes for version
        hasher.update(data)
        hasher.update(bytes(quorum_numbers))
        hasher.update(str(time.time()).encode())  # Add timestamp for uniqueness

        return BlobKey(hasher.digest())
