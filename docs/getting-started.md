# Getting Started with EigenDA Python Client

## Installation

Install the EigenDA Python client using pip:

```bash
pip install eigenda-py
```

Or install from source:

```bash
git clone https://github.com/Layr-Labs/eigenda.git
cd eigenda/python-client
pip install -e .
```

## Configuration

The client requires an Ethereum private key for signing blob dispersal requests. Set this as an environment variable:

```bash
export EIGENDA_PRIVATE_KEY=your_private_key_here
```

Or use a `.env` file:

```bash
cp .env.example .env
# Edit .env with your private key
```

## Basic Usage

```python
from eigenda import DisperserClient, LocalBlobRequestSigner
from eigenda.codec import encode_blob_data

# Initialize signer
signer = LocalBlobRequestSigner("your_private_key_here")

# Create client
client = DisperserClient(
    hostname="disperser-testnet-sepolia.eigenda.xyz",
    port=443,
    use_secure_grpc=True,
    signer=signer
)

# Prepare and encode data
data = b"Hello, EigenDA!"
encoded_data = encode_blob_data(data)

# Disperse blob
status, blob_key = client.disperse_blob(
    data=encoded_data,
    blob_version=0,
    quorum_ids=[0, 1]
)

print(f"Blob Key: {blob_key.hex()}")
print(f"Status: {status}")

# Clean up
client.close()
```

## Using Context Manager

The client supports Python's context manager protocol:

```python
with DisperserClient(
    hostname="disperser-testnet-sepolia.eigenda.xyz",
    port=443,
    use_secure_grpc=True,
    signer=signer
) as client:
    status, blob_key = client.disperse_blob(
        data=encoded_data,
        blob_version=0,
        quorum_ids=[0, 1]
    )
```

## Data Encoding

EigenDA requires data to be encoded in a specific format. The `encode_blob_data` function handles this:

```python
from eigenda.codec import encode_blob_data, decode_blob_data

# Encode data for dispersal
raw_data = b"My data"
encoded = encode_blob_data(raw_data)

# Decode data after retrieval
decoded = decode_blob_data(encoded)
assert decoded == raw_data
```

## Checking Blob Status

After dispersing a blob, you can check its status:

```python
status = client.get_blob_status(blob_key)
print(f"Current status: {status.name}")
```

## Error Handling

```python
try:
    status, blob_key = client.disperse_blob(
        data=encoded_data,
        blob_version=0,
        quorum_ids=[0, 1]
    )
except ValueError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Dispersal failed: {e}")
```

## Network Endpoints

### Testnet (Sepolia)
- Disperser: `disperser-testnet-sepolia.eigenda.xyz:443`
- Explorer: `https://blobs-v2-testnet-sepolia.eigenda.xyz`

### Mainnet
- Disperser: `disperser-mainnet.eigenda.xyz:443`
- Explorer: `https://blobs-v2-mainnet.eigenda.xyz`