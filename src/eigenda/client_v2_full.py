"""EigenDA v2 Disperser Client with full payment support (reservation and on-demand)."""

import time
import grpc
from typing import List, Tuple, Optional, Any
from enum import Enum

from eigenda.core.types import (
    BlobKey, BlobStatus, BlobVersion, QuorumID
)
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2 import DisperserClientV2, DisperserClientConfig
from eigenda.payment import SimpleAccountant, PaymentConfig
from eigenda.grpc.common.v2 import common_v2_pb2
from eigenda.grpc.disperser.v2 import disperser_v2_pb2


class PaymentType(Enum):
    """Payment type for blob dispersal."""
    RESERVATION = "reservation"
    ON_DEMAND = "on_demand"


class DisperserClientV2Full(DisperserClientV2):
    """
    Full-featured disperser client with both reservation and on-demand payment support.

    This client mimics the Go client behavior:
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
        payment_config: Optional[PaymentConfig] = None
    ):
        """
        Initialize the client with full payment support.

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
            hostname=hostname,
            port=port,
            use_secure_grpc=use_secure_grpc,
            timeout=timeout
        )
        super().__init__(hostname, port, use_secure_grpc, signer, config)

        # Payment state
        self.accountant = SimpleAccountant(
            signer.get_account_id(),
            payment_config
        )
        self._payment_state = None
        self._has_reservation = False
        self._payment_type = None

    def _check_payment_state(self) -> None:
        """Check and cache payment state from disperser."""
        try:
            self._payment_state = self.get_payment_state()

            # Check if account has active reservation
            if (hasattr(self._payment_state, 'reservation') and
                    self._payment_state.HasField('reservation')):
                reservation = self._payment_state.reservation
                # Check if reservation is active (has valid timestamps)
                if (hasattr(reservation, 'start_timestamp') and
                    hasattr(reservation, 'end_timestamp') and
                    reservation.start_timestamp > 0 and
                        reservation.end_timestamp > 0):

                    current_time = int(time.time())
                    if reservation.start_timestamp <= current_time <= reservation.end_timestamp:
                        self._has_reservation = True
                        self._payment_type = PaymentType.RESERVATION
                        print(f"  ✓ Active reservation found (ends at {reservation.end_timestamp})")
                        return

            # No active reservation, check on-demand capability
            if hasattr(self._payment_state, 'onchain_cumulative_payment'):
                ocp = self._payment_state.onchain_cumulative_payment
                if ocp and int.from_bytes(ocp, 'big') > 0:
                    self._has_reservation = False
                    self._payment_type = PaymentType.ON_DEMAND

                    # Update accountant with current cumulative payment
                    if hasattr(self._payment_state, 'cumulative_payment'):
                        current = int.from_bytes(self._payment_state.cumulative_payment, 'big')
                        self.accountant.set_cumulative_payment(current)
                        print(f"  ✓ On-demand payment available (current: {current} wei)")
                    return

            # No payment method available
            self._payment_type = None
            print("  ⚠️  No active reservation or on-demand deposit found")

        except Exception as e:
            print(f"  ⚠️  Could not get payment state: {e}")
            self._payment_type = None

    def _create_blob_header(
        self,
        blob_version: BlobVersion,
        blob_commitment: Any,
        quorum_numbers: List[QuorumID]
    ) -> Any:
        """
        Create a protobuf BlobHeader with appropriate payment handling.

        This intelligently chooses between reservation and on-demand payment.
        """
        # Check payment state if not already done
        if self._payment_type is None:
            self._check_payment_state()

        # Get account ID and timestamp
        account_id = self.signer.get_account_id()
        timestamp_ns = int(time.time() * 1e9)

        # Determine payment bytes based on payment type
        payment_bytes = b''

        if self._payment_type == PaymentType.RESERVATION:
            # For reservation, use empty cumulative payment
            payment_bytes = b''
            print("  Using reservation-based payment")

        elif self._payment_type == PaymentType.ON_DEMAND:
            # For on-demand, calculate payment increment
            if hasattr(self, '_last_blob_size'):
                payment_bytes, increment = self.accountant.account_blob(self._last_blob_size)
                print(f"  Using on-demand payment: +{increment} wei ({increment / 1e9:.3f} gwei)")
            else:
                # Fallback to current cumulative payment
                payment_bytes = self.accountant.cumulative_payment.to_bytes(
                    (self.accountant.cumulative_payment.bit_length() + 7) // 8, 'big'
                ) if self.accountant.cumulative_payment > 0 else b''
        else:
            # No payment method available, try empty (might work on some testnets)
            print("  ⚠️  No payment method available, trying with empty payment")
            payment_bytes = b''

        # Create payment header
        payment_header = common_v2_pb2.PaymentHeader(
            account_id=account_id,
            timestamp=timestamp_ns,
            cumulative_payment=payment_bytes
        )

        # Create blob header
        blob_header = common_v2_pb2.BlobHeader(
            version=blob_version,
            commitment=blob_commitment,
            quorum_numbers=quorum_numbers,
            payment_header=payment_header
        )

        return blob_header

    def disperse_blob(
        self,
        data: bytes,
        blob_version: BlobVersion = 0,
        quorum_ids: Optional[List[QuorumID]] = None,
        timeout: Optional[int] = None
    ) -> Tuple[BlobStatus, BlobKey]:
        """
        Disperse a blob with automatic payment method selection.

        Tries reservation first, falls back to on-demand if needed.
        """
        print(f"\nDispersing blob ({len(data)} bytes)...")

        # Store blob size for on-demand payment calculation
        self._last_blob_size = len(data)

        # First attempt
        try:
            status, blob_key = super().disperse_blob(data, blob_version, quorum_ids, timeout)
            return (status, blob_key)  # Return tuple as expected
        except Exception as e:
            error_msg = str(e)

            # If it's a reservation error and we haven't tried on-demand yet
            if ("reservation" in error_msg.lower() and
                "not a valid active reservation" in error_msg and
                    self._payment_type != PaymentType.ON_DEMAND):

                print("  Reservation failed, retrying with on-demand payment...")

                # Force switch to on-demand
                self._payment_type = PaymentType.ON_DEMAND
                self._has_reservation = False

                # Refresh payment state to get latest cumulative payment
                self._check_payment_state()

                # Retry
                status, blob_key = super().disperse_blob(data, blob_version, quorum_ids, timeout)
                return (status, blob_key)  # Return tuple as expected
            else:
                # Re-raise other errors
                raise

    def get_blob_status(self, blob_key: str) -> Any:
        """
        Get the status of a dispersed blob.

        Args:
            blob_key: The blob key as a hex string

        Returns:
            The full blob status response (not just the status enum)
        """
        self._connect()

        # Convert hex string to bytes
        blob_key_bytes = bytes.fromhex(blob_key)

        request = disperser_v2_pb2.BlobStatusRequest(
            blob_key=blob_key_bytes
        )

        try:
            response = self._stub.GetBlobStatus(
                request,
                timeout=self.config.timeout,
                metadata=self._get_metadata()
            )

            # Return the full response, not just the parsed status
            return response

        except grpc.RpcError as e:
            raise Exception(f"gRPC error: {e.code()} - {e.details()}")

    def get_payment_info(self) -> dict:
        """Get information about current payment configuration."""
        if self._payment_state is None:
            self._check_payment_state()

        info = {
            "payment_type": self._payment_type.value if self._payment_type else "none",
            "has_reservation": self._has_reservation,
        }

        if self._payment_type == PaymentType.ON_DEMAND:
            info["current_cumulative_payment"] = self.accountant.cumulative_payment
            info["price_per_symbol"] = self.accountant.config.price_per_symbol
            info["min_symbols"] = self.accountant.config.min_num_symbols

        return info
