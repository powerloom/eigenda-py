"""EigenDA v2 Disperser Client with full gRPC implementation."""

import time
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple, Union

import grpc

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.core.types import BlobKey, BlobStatus, BlobVersion, QuorumID
from eigenda.grpc.common.v2 import common_v2_pb2

# Import generated gRPC code
from eigenda.grpc.disperser.v2 import disperser_v2_pb2, disperser_v2_pb2_grpc


@dataclass
class DisperserClientConfig:
    """Configuration for the disperser client."""

    hostname: str
    port: int
    use_secure_grpc: bool = True
    timeout: int = 30


class DisperserClientV2:
    """Full implementation of EigenDA v2 Disperser Client."""

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
        self._stub: Optional[disperser_v2_pb2_grpc.DisperserStub] = None
        self._connected = False

    def _connect(self):
        """Establish gRPC connection and create stub."""
        if self._connected:
            return

        target = f"{self.hostname}:{self.port}"

        # Set up channel options
        options = [
            ("grpc.max_receive_message_length", 16 * 1024 * 1024),  # 16MB
            ("grpc.max_send_message_length", 16 * 1024 * 1024),  # 16MB
        ]

        if self.use_secure_grpc:
            credentials = grpc.ssl_channel_credentials()
            self._channel = grpc.secure_channel(target, credentials, options)
        else:
            self._channel = grpc.insecure_channel(target, options)

        self._stub = disperser_v2_pb2_grpc.DisperserStub(self._channel)
        self._connected = True

    def disperse_blob(
        self,
        data: bytes,
        blob_version: BlobVersion,
        quorum_ids: List[QuorumID],
        timeout: Optional[int] = None,
    ) -> Tuple[BlobStatus, BlobKey]:
        """
        Disperse a blob to the EigenDA network.

        Args:
            data: The encoded blob data to disperse
            blob_version: Version of the blob format
            quorum_ids: List of quorum IDs to disperse to
            timeout: Optional timeout in seconds

        Returns:
            Tuple of (status, blob_key)
        """
        self._connect()

        # Validate data
        if len(data) == 0:
            raise ValueError("Data cannot be empty")
        if len(data) > 16 * 1024 * 1024:  # 16 MiB limit
            raise ValueError("Data exceeds maximum size of 16 MiB")

        # For now, we'll get the commitment from the disperser
        # In a production implementation, this could be calculated locally
        commitment_reply = self.get_blob_commitment(data)

        # Create blob header
        blob_header = self._create_blob_header(
            blob_version=blob_version,
            blob_commitment=commitment_reply.blob_commitment,
            quorum_numbers=quorum_ids,
        )

        # Sign the blob header
        signature = self.signer.sign_blob_request(blob_header)

        # Create the protobuf request
        request = disperser_v2_pb2.DisperseBlobRequest(
            blob=data, blob_header=blob_header, signature=signature
        )

        # Make the gRPC call
        try:
            time.time() + (timeout or self.config.timeout)
            response = self._stub.DisperseBlob(
                request, timeout=timeout or self.config.timeout, metadata=self._get_metadata()
            )

            # Parse response
            status = self._parse_blob_status(response.result)
            blob_key = BlobKey(response.blob_key)

            return (status, blob_key)

        except grpc.RpcError as e:
            raise Exception(f"gRPC error: {e.code()} - {e.details()}")

    def get_blob_status(self, blob_key: Union[BlobKey, str]) -> Any:
        """
        Get the status of a dispersed blob.

        Args:
            blob_key: The unique identifier of the blob

        Returns:
            The BlobStatusReply containing status and inclusion info
        """
        self._connect()

        # Handle both BlobKey objects and hex strings
        if isinstance(blob_key, str):
            blob_key = BlobKey.from_hex(blob_key)

        request = disperser_v2_pb2.BlobStatusRequest(blob_key=bytes(blob_key))

        try:
            response = self._stub.GetBlobStatus(
                request, timeout=self.config.timeout, metadata=self._get_metadata()
            )

            return response

        except grpc.RpcError as e:
            raise Exception(f"gRPC error: {e.code()} - {e.details()}")

    def get_blob_commitment(self, data: bytes) -> Any:
        """
        Get blob commitment from the disperser.

        Args:
            data: The blob data

        Returns:
            BlobCommitmentReply containing the commitment
        """
        self._connect()

        request = disperser_v2_pb2.BlobCommitmentRequest(blob=data)

        try:
            response = self._stub.GetBlobCommitment(
                request, timeout=self.config.timeout, metadata=self._get_metadata()
            )

            return response

        except grpc.RpcError as e:
            raise Exception(f"gRPC error: {e.code()} - {e.details()}")

    def get_payment_state(self, timestamp: Optional[int] = None) -> Any:
        """
        Get payment state for the signer's account.

        Args:
            timestamp: Optional timestamp in nanoseconds (defaults to current time)

        Returns:
            Payment state information
        """
        self._connect()

        if timestamp is None:
            timestamp = int(time.time() * 1e9)  # Current time in nanoseconds

        account_id = self.signer.get_account_id()
        signature = self.signer.sign_payment_state_request(timestamp)

        request = disperser_v2_pb2.GetPaymentStateRequest(
            account_id=account_id, signature=signature, timestamp=timestamp
        )

        try:
            response = self._stub.GetPaymentState(
                request, timeout=self.config.timeout, metadata=self._get_metadata()
            )

            return response

        except grpc.RpcError as e:
            raise Exception(f"gRPC error: {e.code()} - {e.details()}")

    def close(self):
        """Close the gRPC connection."""
        if self._channel:
            self._channel.close()
            self._connected = False
            self._channel = None
            self._stub = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _create_blob_header(
        self, blob_version: BlobVersion, blob_commitment: Any, quorum_numbers: List[QuorumID]
    ) -> Any:
        """
        Create a protobuf BlobHeader.

        Args:
            blob_version: Blob format version
            blob_commitment: The blob commitment from disperser
            quorum_numbers: List of quorum IDs

        Returns:
            Protobuf BlobHeader message
        """
        # Create payment header
        account_id = self.signer.get_account_id()
        # Get current timestamp in nanoseconds
        timestamp_ns = int(time.time() * 1e9)

        payment_header = common_v2_pb2.PaymentHeader(
            account_id=account_id,
            timestamp=timestamp_ns,
            cumulative_payment=b"",  # Empty for reservation-based payment
        )

        # Create blob header
        blob_header = common_v2_pb2.BlobHeader(
            version=blob_version,
            commitment=blob_commitment,
            quorum_numbers=quorum_numbers,
            payment_header=payment_header,
        )

        return blob_header

    def _parse_blob_status(self, proto_status: Any) -> BlobStatus:
        """Parse protobuf BlobStatus to our enum."""
        # Map from protobuf status to our enum
        status_map = {
            0: BlobStatus.UNKNOWN,
            1: BlobStatus.QUEUED,
            2: BlobStatus.ENCODED,
            3: BlobStatus.GATHERING_SIGNATURES,
            4: BlobStatus.COMPLETE,
            5: BlobStatus.FAILED,
        }

        return status_map.get(proto_status, BlobStatus.UNKNOWN)

    def _get_metadata(self) -> List[Tuple[str, str]]:
        """Get metadata for gRPC calls."""
        return [
            ("user-agent", "eigenda-python-client/0.1.0"),
        ]
