"""
DisperserClientV2Full - A simplified version with payment handling.

This is a higher-level client that handles payment state automatically.
It simplifies blob dispersal by:
1. Tries to use reservation first (if available)
2. Falls back to on-demand payment if no reservation
3. Handles payment state tracking automatically
"""

import time
from typing import Any, List, Optional, Tuple

import grpc

from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2 import DisperserClientConfig, DisperserClientV2
from eigenda.codec.blob_codec import encode_blob_data
from eigenda.core.types import BlobKey, BlobStatus, PaymentType, QuorumID
from eigenda.grpc.common.v2 import common_v2_pb2
from eigenda.grpc.disperser.v2 import disperser_v2_pb2
from eigenda.payment import PaymentConfig, SimpleAccountant


class DisperserClientV2Full(DisperserClientV2):
    """
    Extended DisperserClient with automatic payment handling.

    This client automatically handles both reservation-based and on-demand payments.
    It intelligently chooses the payment method based on availability:
    1. Tries to use reservation first (if available)
    2. Falls back to on-demand payment if no reservation
    3. Handles payment state tracking automatically
    """

    def __init__(
        self,
        hostname: str,
        port: int,
        use_secure_grpc: bool,
        signer: LocalBlobRequestSigner,
        timeout: int = 30,
        payment_config: Optional[PaymentConfig] = None,
    ):
        """
        Initialize the client with payment support.

        Args:
            hostname: Disperser service hostname
            port: Disperser service port
            use_secure_grpc: Whether to use TLS
            signer: Request signer for authentication
            timeout: Request timeout in seconds
            payment_config: Optional payment configuration for on-demand
        """
        # Initialize parent
        config = DisperserClientConfig(
            hostname=hostname, port=port, use_secure_grpc=use_secure_grpc, timeout=timeout
        )
        super().__init__(hostname, port, use_secure_grpc, signer, config)

        # Payment configuration
        self.payment_config = payment_config or PaymentConfig()

        # Payment state
        self.accountant = None  # Will be initialized based on payment state
        self._payment_state = None
        self._has_reservation = False
        self._payment_type = None

    def _check_payment_state(self) -> None:
        """Check and cache payment state from disperser."""
        try:
            self._payment_state = self.get_payment_state()
            self._process_payment_state()

        except Exception as e:
            print(f"  ⚠️  Could not get payment state: {e}")
            self._payment_type = None

    def _process_payment_state(self) -> None:
        """Process simple payment state and determine payment type."""
        if not self._payment_state:
            print("  ⚠️  No payment state received")
            self._payment_type = None
            return

        # Update payment config from global params if available
        if hasattr(self._payment_state, "payment_global_params"):
            params = self._payment_state.payment_global_params
            if params:
                self.payment_config.price_per_symbol = params.price_per_symbol
                self.payment_config.min_num_symbols = params.min_num_symbols

        # Check for reservation
        if hasattr(self._payment_state, "reservation") and self._payment_state.HasField(
            "reservation"
        ):
            reservation = self._payment_state.reservation

            # Check if reservation is active
            current_time = int(time.time())
            if reservation.start_timestamp <= current_time <= reservation.end_timestamp:
                self._has_reservation = True
                self._payment_type = PaymentType.RESERVATION

                # Create simple accountant for reservation
                self.accountant = SimpleAccountant(
                    self.signer.get_account_id(), self.payment_config
                )

                expires_in = reservation.end_timestamp - current_time
                print(f"  ✓ Active reservation found (expires in {expires_in}s)")
                return

        # Check for on-demand payment
        if hasattr(self._payment_state, "onchain_cumulative_payment"):
            ocp = self._payment_state.onchain_cumulative_payment
            if ocp and len(ocp) > 0:
                amount = int.from_bytes(ocp, "big")
                if amount > 0:
                    print(f"  ✓ On-demand deposit found: {amount} wei ({amount/1e18:.4f} ETH)")
                else:
                    print("  ⚠️  On-demand deposit is zero")

                self._has_reservation = False
                self._payment_type = PaymentType.ON_DEMAND

                # Create simple accountant for on-demand
                self.accountant = SimpleAccountant(
                    self.signer.get_account_id(), self.payment_config
                )

                # Update accountant with current cumulative payment
                if hasattr(self._payment_state, "cumulative_payment"):
                    current = int.from_bytes(self._payment_state.cumulative_payment, "big")
                    self.accountant.set_cumulative_payment(current)
                    print(
                        f"  ✓ On-demand payment available "
                        f"(server cumulative: {current} wei / {current/1e9:.3f} gwei)"
                    )
                return

        # No payment method available
        self._payment_type = None
        print("  ⚠️  No active reservation or on-demand deposit found")

    def _create_blob_header(
        self, blob_version: Any, blob_commitment: Any, quorum_numbers: List[QuorumID]
    ) -> Any:
        """
        Create a protobuf BlobHeader with appropriate payment handling.

        This intelligently chooses between reservation and on-demand payment.
        """
        # Check payment state if not already done or if using on-demand
        # For on-demand, we need to refresh state to get latest cumulative payment
        if self._payment_type is None or self._payment_type == PaymentType.ON_DEMAND:
            self._check_payment_state()

        if self.accountant is None:
            # No accountant available, create simple one
            self.accountant = SimpleAccountant(self.signer.get_account_id(), self.payment_config)

        # Get account ID and timestamp
        account_id = self.signer.get_account_id()
        timestamp_ns = int(time.time() * 1e9)

        # Determine payment bytes based on payment type
        payment_bytes = b""

        if self._payment_type == PaymentType.RESERVATION:
            # Simple reservation
            payment_bytes = b""
            print("  Using reservation-based payment")

        elif self._payment_type == PaymentType.ON_DEMAND:
            # Simple on-demand
            if hasattr(self, "_last_blob_size"):
                payment_bytes, increment = self.accountant.account_blob(self._last_blob_size)
                print(f"  Using on-demand payment: +{increment} wei ({increment / 1e9:.3f} gwei)")
            else:
                # Fallback to current cumulative payment
                payment_bytes = (
                    self.accountant.cumulative_payment.to_bytes(
                        (self.accountant.cumulative_payment.bit_length() + 7) // 8, "big"
                    )
                    if self.accountant.cumulative_payment > 0
                    else b""
                )
        else:
            # No payment method available - fail with clear error
            raise ValueError(
                "No payment method available. Please either:\n"
                "  1. Make an on-demand deposit to the PaymentVault contract\n"
                "  2. Purchase a reservation\n"
                "  3. Use the testnet with an account that has payment set up"
            )

        # Create payment header
        payment_header = common_v2_pb2.PaymentHeader(
            account_id=account_id, timestamp=timestamp_ns, cumulative_payment=payment_bytes
        )

        # Create blob header
        blob_header = common_v2_pb2.BlobHeader(
            version=blob_version,
            commitment=blob_commitment,
            quorum_numbers=quorum_numbers,
            payment_header=payment_header,
        )

        return blob_header

    def disperse_blob(
        self,
        data: bytes,
        quorum_numbers: Optional[List[int]] = None,
        blob_version: int = 0,
    ) -> Tuple[BlobStatus, BlobKey]:
        """
        Disperse a blob with automatic payment handling.

        Args:
            data: Raw data to disperse
            quorum_numbers: Optional list of quorum IDs (defaults to [0, 1])
            blob_version: Blob version (default 0)

        Returns:
            Tuple of (blob_key, request_id)
        """
        # Set default quorums if not provided
        if quorum_numbers is None:
            quorum_numbers = [0, 1]

        # Validate data
        if len(data) == 0:
            raise ValueError("Data cannot be empty")
        if len(data) > 16 * 1024 * 1024:  # 16 MiB limit
            raise ValueError("Data exceeds maximum size of 16 MiB")

        # Encode the data
        encoded_data = encode_blob_data(data)

        # Store blob size for payment calculation
        self._last_blob_size = len(encoded_data)

        # Get blob commitment
        commitment_reply = self.get_blob_commitment(encoded_data)
        # Extract the actual commitment from the reply
        commitment = (
            commitment_reply.blob_commitment
            if hasattr(commitment_reply, "blob_commitment")
            else commitment_reply
        )

        # Create blob header with payment
        blob_header = self._create_blob_header(blob_version, commitment, quorum_numbers)

        # Sign the blob header
        signature = self.signer.sign_blob_request(blob_header)

        # Create the protobuf request
        request = disperser_v2_pb2.DisperseBlobRequest(
            blob=encoded_data, blob_header=blob_header, signature=signature
        )

        # Make the gRPC call
        self._connect()
        try:
            response = self._stub.DisperseBlob(
                request, timeout=self.config.timeout, metadata=self._get_metadata()
            )

            # Parse response
            status = self._parse_blob_status(response.result)
            blob_key = BlobKey(response.blob_key)

            return (status, blob_key)

        except grpc.RpcError as e:
            raise Exception(f"gRPC error: {e.code()} - {e.details()}")

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

    def get_payment_state(self) -> Any:
        """
        Get payment state for the account.

        Returns:
            The payment state response
        """
        self._connect()

        # Create signature for authentication
        timestamp_ns = int(time.time() * 1e9)
        signature = self.signer.sign_payment_state_request(timestamp_ns)

        request = disperser_v2_pb2.GetPaymentStateRequest(
            account_id=self.signer.get_account_id(), timestamp=timestamp_ns, signature=signature
        )

        try:
            response = self._stub.GetPaymentState(
                request, timeout=self.config.timeout, metadata=self._get_metadata()
            )
            return response
        except grpc.RpcError as e:
            # If method not implemented, return None
            if e.code() == grpc.StatusCode.UNIMPLEMENTED:
                return None
            raise

    def get_payment_info(self) -> dict:
        """
        Get current payment information for the account.

        Returns:
            Dictionary containing payment information:
            - payment_type: "reservation", "on_demand", or None
            - has_reservation: bool
            - reservation_details: dict with reservation info (if active)
            - current_cumulative_payment: int (wei)
            - onchain_balance: int (wei)
            - price_per_symbol: int (wei)
            - min_symbols: int
        """
        # Check payment state if not cached
        if self._payment_state is None:
            self._check_payment_state()

        info = {
            "payment_type": self._payment_type.value if self._payment_type else None,
            "has_reservation": self._has_reservation,
            "reservation_details": None,
            "current_cumulative_payment": 0,
            "onchain_balance": 0,
            "price_per_symbol": self.payment_config.price_per_symbol,
            "min_symbols": self.payment_config.min_num_symbols,
        }

        if self._payment_state:
            # Add reservation details if present
            if self._has_reservation and hasattr(self._payment_state, "reservation"):
                reservation = self._payment_state.reservation
                current_time = int(time.time())
                info["reservation_details"] = {
                    "symbols_per_second": reservation.symbols_per_second,
                    "start_timestamp": reservation.start_timestamp,
                    "end_timestamp": reservation.end_timestamp,
                    "time_remaining": max(0, reservation.end_timestamp - current_time),
                    "quorum_numbers": list(reservation.quorum_numbers),
                    "quorum_splits": list(reservation.quorum_splits),
                }

            # Add payment amounts
            if hasattr(self._payment_state, "cumulative_payment"):
                info["current_cumulative_payment"] = int.from_bytes(
                    self._payment_state.cumulative_payment, "big"
                )

            if hasattr(self._payment_state, "onchain_cumulative_payment"):
                info["onchain_balance"] = int.from_bytes(
                    self._payment_state.onchain_cumulative_payment, "big"
                )

        return info
