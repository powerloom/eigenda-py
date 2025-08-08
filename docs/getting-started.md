# Getting Started with EigenDA Python Client

## Installation

Install the EigenDA Python client using pip:

```bash
pip install powerloom-eigenda
```

Or install from source using UV:

```bash
git clone https://github.com/powerloom/eigenda-py powerloom-eigenda
cd powerloom-eigenda

# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies for development (recommended)
uv sync --all-extras

# This installs everything including dev tools
# After this, you can run commands without additional flags:
# uv run pytest tests/
# uv run python examples/minimal_client.py
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

## Basic Usage (Recommended - Automatic Payment Handling)

```python
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full

# Initialize signer
signer = LocalBlobRequestSigner("your_private_key_here")

# Create client (automatically handles payments)
client = DisperserClientV2Full(
    hostname="disperser-testnet-sepolia.eigenda.xyz",
    port=443,
    use_secure_grpc=True,
    signer=signer
)

# Disperse blob (no encoding needed - handled automatically)
data = b"Hello, EigenDA!"
status, blob_key = client.disperse_blob(
    data=data,  # Pass raw data directly
    quorum_numbers=[0, 1]  # Note: quorum_numbers for V2Full
)

print(f"Blob Key: {blob_key.hex()}")
print(f"Status: {status.name}")

# Check payment info
payment_info = client.get_payment_info()
print(f"Payment type: {payment_info['payment_type']}")

# Clean up
client.close()
```

The `DisperserClientV2Full` automatically:
- Encodes your data
- Checks for active reservations (no ETH charges)
- Falls back to on-demand payment if needed
- Handles all payment calculations

## Using Context Manager

The client supports Python's context manager protocol:

```python
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full

signer = LocalBlobRequestSigner("your_private_key_here")

with DisperserClientV2Full(
    hostname="disperser-testnet-sepolia.eigenda.xyz",
    port=443,
    use_secure_grpc=True,
    signer=signer
) as client:
    status, blob_key = client.disperse_blob(
        data=b"Hello, EigenDA!",
        quorum_numbers=[0, 1]
    )
    print(f"Blob Key: {blob_key.hex()}")
```

## Data Encoding

When using `DisperserClientV2Full`, encoding is handled automatically. If you need manual control:

```python
from eigenda.codec.blob_codec import encode_blob_data, decode_blob_data

# DisperserClientV2Full handles this automatically
# But if using DisperserClientV2 or for manual encoding:
raw_data = b"My data"
encoded = encode_blob_data(raw_data)

# Decode data after retrieval
decoded = decode_blob_data(encoded, len(raw_data))
assert decoded == raw_data
```

**Note:** `DisperserClientV2Full` encodes data automatically, while `DisperserClientV2` requires pre-encoded data.

## Checking Blob Status

After dispersing a blob, you can check its status:

```python
from eigenda.core.types import BlobStatus

# Get status (pass hex string)
response = client.get_blob_status(blob_key.hex())

# Parse the status
status = BlobStatus(response.status)
print(f"Current status: {status.name}")

# Status values:
# - QUEUED: Blob is waiting to be processed
# - ENCODED: Blob has been encoded
# - GATHERING_SIGNATURES: Collecting signatures from nodes
# - COMPLETE: Successfully dispersed
# - FAILED: Dispersal failed
```

## Error Handling

```python
try:
    status, blob_key = client.disperse_blob(
        data=b"Hello, EigenDA!",
        quorum_numbers=[0, 1]
    )
except ValueError as e:
    print(f"Invalid input: {e}")
    # Common causes:
    # - Empty data
    # - Data exceeds 16 MiB limit
    # - No payment method available
except Exception as e:
    print(f"Dispersal failed: {e}")
```

## Payment Methods

The client automatically detects and uses the best payment method:

```python
# Check payment information
payment_info = client.get_payment_info()

if payment_info['payment_type'] == 'reservation':
    # Using pre-paid reservation (no per-blob charges)
    print(f"Bandwidth: {payment_info['reservation_details']['symbols_per_second']} symbols/sec")
    print(f"Time remaining: {payment_info['reservation_details']['time_remaining']} seconds")
elif payment_info['payment_type'] == 'on_demand':
    # Using on-demand payment (ETH charged per blob)
    print(f"Balance: {payment_info['onchain_balance']/1e18:.4f} ETH")
    print(f"Used: {payment_info['current_cumulative_payment']/1e18:.4f} ETH")
else:
    print("No payment method available!")
    print("Please deposit ETH to PaymentVault or purchase a reservation")
```

## Network Endpoints

### Testnet (Sepolia) - Default
- Disperser: `disperser-testnet-sepolia.eigenda.xyz:443`
- Explorer: `https://blobs-v2-testnet-sepolia.eigenda.xyz`
- PaymentVault: `0x2E1BDB221E7D6bD9B7b2365208d41A5FD70b24Ed`

### Testnet (Holesky)
- Disperser: `disperser-testnet-holesky.eigenda.xyz:443`
- Explorer: `https://blobs-v2-testnet-holesky.eigenda.xyz`
- PaymentVault: `0x4a7Fff191BCDa5806f1Bc8689afc1417c08C61AB`

### Mainnet
- Disperser: `disperser.eigenda.xyz:443`
- Explorer: `https://blobs.eigenda.xyz`
- PaymentVault: `0xb2e7ef419a2A399472ae22ef5cFcCb8bE97A4B05`

## Examples

The `examples/` directory contains working examples for various use cases:

- `minimal_client.py` - Simplest example using mock client
- `full_example.py` - Complete dispersal workflow
- `test_reservation_account.py` - Check if account has reservation
- `test_both_payments.py` - Test different payment methods
- `check_blob_status.py` - Monitor blob status
- `check_payment_vault.py` - Check on-chain payment status

Run any example:
```bash
uv run python examples/minimal_client.py
```
