"""EigenDA Python Client - A Python implementation of the EigenDA v2 client."""

from eigenda._version import __version__, __version_info__
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client import DisperserClient as MockDisperserClient
from eigenda.client_v2 import DisperserClientV2
from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.codec import decode_blob_data, encode_blob_data
from eigenda.core.types import BlobKey, BlobStatus, BlobVersion
from eigenda.payment import PaymentConfig
from eigenda.retriever import BlobRetriever

__all__ = [
    # Version
    "__version__",
    "__version_info__",
    # Clients
    "MockDisperserClient",  # Mock client for testing
    "DisperserClientV2",  # Basic v2 client
    "DisperserClientV2Full",  # Full client with payment support
    "BlobRetriever",
    # Authentication
    "LocalBlobRequestSigner",
    # Types
    "BlobKey",
    "BlobStatus",
    "BlobVersion",
    "PaymentConfig",
    # Utilities
    "encode_blob_data",
    "decode_blob_data",
]
