# API Reference

## Core Classes

### DisperserClientV2

Full implementation of the EigenDA v2 disperser client with gRPC communication.

```python
class DisperserClientV2:
    def __init__(
        self,
        hostname: str,
        port: int,
        use_secure_grpc: bool,
        signer: LocalBlobRequestSigner,
        config: Optional[DisperserClientConfig] = None
    )
```

**Parameters:**
- `hostname`: Disperser service hostname
- `port`: Disperser service port
- `use_secure_grpc`: Whether to use TLS connection
- `signer`: Request signer for authentication
- `config`: Optional additional configuration

**Methods:**

#### disperse_blob
```python
def disperse_blob(
    self,
    data: bytes,
    blob_version: BlobVersion,
    quorum_ids: List[QuorumID],
    timeout: Optional[int] = None
) -> Tuple[BlobStatus, BlobKey]
```

Disperse a blob to the EigenDA network using gRPC.

#### get_blob_status
```python
def get_blob_status(self, blob_key: BlobKey) -> BlobStatus
```

Get the current status of a dispersed blob.

#### get_blob_commitment
```python
def get_blob_commitment(self, data: bytes) -> Any
```

Get blob commitment from the disperser (useful if you don't have local proving capability).

#### get_payment_state
```python
def get_payment_state(self, timestamp: Optional[int] = None) -> Any
```

Get payment state for the signer's account.

### DisperserClient

Main client for interacting with EigenDA disperser service.

```python
class DisperserClient:
    def __init__(
        self,
        hostname: str,
        port: int,
        use_secure_grpc: bool,
        signer: LocalBlobRequestSigner,
        config: Optional[DisperserClientConfig] = None
    )
```

**Parameters:**
- `hostname`: Disperser service hostname
- `port`: Disperser service port
- `use_secure_grpc`: Whether to use TLS connection
- `signer`: Request signer for authentication
- `config`: Optional additional configuration

**Methods:**

#### disperse_blob
```python
def disperse_blob(
    self,
    data: bytes,
    blob_version: BlobVersion,
    quorum_ids: List[QuorumID],
    timeout: Optional[int] = None
) -> Tuple[BlobStatus, BlobKey]
```

Disperse a blob to the EigenDA network.

**Parameters:**
- `data`: Encoded blob data (use `encode_blob_data()`)
- `blob_version`: Version of blob format (currently 0)
- `quorum_ids`: List of quorum IDs (e.g., [0, 1])
- `timeout`: Optional timeout in seconds

**Returns:**
- Tuple of (status, blob_key)

#### get_blob_status
```python
def get_blob_status(self, blob_key: BlobKey) -> BlobStatus
```

Get the current status of a dispersed blob.

#### close
```python
def close(self)
```

Close the gRPC connection.

### BlobRetriever

Client for retrieving blobs from EigenDA.

```python
class BlobRetriever:
    def __init__(
        self,
        hostname: str,
        port: int,
        use_secure_grpc: bool,
        signer: Optional[LocalBlobRequestSigner] = None,
        config: Optional[RetrieverConfig] = None
    )
```

**Methods:**

#### retrieve_blob
```python
def retrieve_blob(self, blob_key: BlobKey) -> bytes
```

Retrieve a blob from EigenDA.

**Parameters:**
- `blob_key`: The unique identifier of the blob

**Returns:**
- The encoded blob data

#### get_blob_info
```python
def get_blob_info(self, blob_key: BlobKey) -> Tuple[int, int]
```

Get metadata about a blob without retrieving its data.

**Returns:**
- Tuple of (blob_size, encoding_version)

### LocalBlobRequestSigner

Signs blob requests using an Ethereum private key.

```python
class LocalBlobRequestSigner:
    def __init__(self, private_key_hex: str)
```

**Methods:**

#### get_account_id
```python
def get_account_id(self) -> Address
```

Get the Ethereum address associated with this signer.

## Types

### BlobKey

Unique 32-byte identifier for a blob.

```python
class BlobKey:
    def hex(self) -> str

    @classmethod
    def from_hex(cls, hex_str: str) -> BlobKey

    @classmethod
    def from_bytes(cls, data: bytes) -> BlobKey
```

### BlobStatus

Enum representing blob dispersal status:

- `UNKNOWN` = 0
- `PROCESSING` = 1
- `GATHERING_SIGNATURES` = 2
- `COMPLETE` = 3
- `FAILED` = 4
- `INSUFFICIENT_SIGNATURES` = 5

### BlobVersion

Type alias for int representing the blob format version.

### QuorumID

Type alias for int representing a quorum identifier.

## Utility Functions

### encode_blob_data
```python
def encode_blob_data(data: bytes) -> bytes
```

Encode raw data for EigenDA dispersal by adding padding bytes.

**Parameters:**
- `data`: Raw data to encode

**Returns:**
- Encoded data ready for dispersal

### decode_blob_data
```python
def decode_blob_data(encoded_data: bytes) -> bytes
```

Decode blob data by removing padding bytes.

**Parameters:**
- `encoded_data`: Encoded blob data

**Returns:**
- Original raw data
