"""Blob retrieval functionality for EigenDA."""

from dataclasses import dataclass
from typing import Any, Optional

import grpc

from eigenda.auth.signer import LocalBlobRequestSigner

# Import generated gRPC code
from eigenda.grpc.retriever.v2 import retriever_v2_pb2, retriever_v2_pb2_grpc


@dataclass
class RetrieverConfig:
    """Configuration for the retriever client."""

    hostname: str
    port: int
    use_secure_grpc: bool = True
    timeout: int = 60  # Retrieval may take longer


class BlobRetriever:
    """Client for retrieving blobs from EigenDA."""

    def __init__(
        self,
        hostname: str,
        port: int,
        use_secure_grpc: bool,
        signer: Optional[LocalBlobRequestSigner] = None,
        config: Optional[RetrieverConfig] = None,
    ):
        """
        Initialize the retriever client.

        Args:
            hostname: Retriever service hostname
            port: Retriever service port
            use_secure_grpc: Whether to use TLS
            signer: Optional request signer for authentication
            config: Optional additional configuration
        """
        self.hostname = hostname
        self.port = port
        self.use_secure_grpc = use_secure_grpc
        self.signer = signer
        self.config = config or RetrieverConfig(
            hostname=hostname, port=port, use_secure_grpc=use_secure_grpc
        )

        self._channel: Optional[grpc.Channel] = None
        self._stub: Optional[retriever_v2_pb2_grpc.RetrieverStub] = None
        self._connected = False

    def _connect(self):
        """Establish gRPC connection and create stub."""
        if self._connected:
            return

        target = f"{self.hostname}:{self.port}"

        # Set up channel options
        options = [
            ("grpc.max_receive_message_length", 32 * 1024 * 1024),  # 32MB for retrieved data
            ("grpc.max_send_message_length", 1 * 1024 * 1024),  # 1MB for requests
        ]

        if self.use_secure_grpc:
            credentials = grpc.ssl_channel_credentials()
            self._channel = grpc.secure_channel(target, credentials, options)
        else:
            self._channel = grpc.insecure_channel(target, options)

        self._stub = retriever_v2_pb2_grpc.RetrieverStub(self._channel)
        self._connected = True

    def retrieve_blob(self, blob_header: Any, reference_block_number: int, quorum_id: int) -> bytes:
        """
        Retrieve a blob from EigenDA nodes.

        Args:
            blob_header: The blob header from dispersal
            reference_block_number: The Ethereum block number when blob was dispersed
            quorum_id: Which quorum to retrieve from

        Returns:
            The encoded blob data
        """
        self._connect()

        request = retriever_v2_pb2.BlobRequest(
            blob_header=blob_header,
            reference_block_number=reference_block_number,
            quorum_id=quorum_id,
        )

        try:
            response = self._stub.RetrieveBlob(
                request, timeout=self.config.timeout, metadata=self._get_metadata()
            )

            # The response contains the encoded blob data
            return response.data

        except grpc.RpcError as e:
            raise Exception(f"gRPC error retrieving blob: {e.code()} - {e.details()}")

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

    def _get_metadata(self) -> list:
        """Get metadata for gRPC calls."""
        metadata = [("user-agent", "eigenda-python-retriever/0.1.0")]

        # Add authentication if signer is provided
        if self.signer:
            account_id = self.signer.get_account_id()
            metadata.append(("account-id", account_id))

        return metadata
