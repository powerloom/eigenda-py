# EigenDA Python Client

A Python implementation of the EigenDA v2 client for interacting with the EigenDA protocol.

## Overview

This client provides a Python interface to EigenDA, a decentralized data availability service. It includes full authentication support and compatibility with the official Go and Rust implementations.

## Status

✅ **Fully Working!** - The client successfully disperses blobs to EigenDA using both reservation-based and on-demand payments.

### Implemented Features
- Full gRPC v2 protocol support
- ECDSA signature authentication
- BN254 field element encoding
- G1/G2 point decompression (gnark-crypto compatible)
- Payment state queries
- **Dual payment support**:
  - ✅ Reservation-based payments (pre-paid bandwidth)
  - ✅ On-demand payments (pay per blob)
- Automatic payment method selection
- Proper payment calculation based on blob size

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

1. **Set Environment Variables**
```bash
# Create .env file
cp .env.example .env

# Add your private key
echo "EIGENDA_PRIVATE_KEY=your_private_key_here" >> .env
```

2. **Run Examples**
```bash
# Examples can now be run directly without setting PYTHONPATH
python examples/minimal_client.py

# Or run other examples
python examples/full_example.py
python examples/check_payment_vault.py
```

## Configuration

### Network Selection

The client automatically detects the network based on the `EIGENDA_DISPERSER_HOST` environment variable:

```bash
# Sepolia testnet
EIGENDA_DISPERSER_HOST=disperser-testnet-sepolia.eigenda.xyz

# Holesky testnet (default)
EIGENDA_DISPERSER_HOST=disperser-testnet-holesky.eigenda.xyz

# Mainnet
EIGENDA_DISPERSER_HOST=disperser.eigenda.xyz
```

### PaymentVault Configuration

The client uses the appropriate PaymentVault contract for each network:

| Network | PaymentVault Address | Price per Symbol | Min Symbols | Min Cost |
|---------|---------------------|------------------|-------------|----------|
| Sepolia | `0x2E1BDB221E7D6bD9B7b2365208d41A5FD70b24Ed` | 447 gwei | 4,096 | 1,830.912 gwei |
| Holesky | `0x4a7Fff191BCDa5806f1Bc8689afc1417c08C61AB` | 447 gwei | 4,096 | 1,830.912 gwei |
| Mainnet | `0xb2e7ef419a2A399472ae22ef5cFcCb8bE97A4B05` | 447 gwei | 4,096 | 1,830.912 gwei |

All networks currently have the same pricing structure.

## Usage

### Basic Example (Mock Client)

```python
from eigenda import MockDisperserClient
from eigenda.core.types import BlobStatus

# Initialize client
client = MockDisperserClient()

# Disperse data
data = b"Hello, EigenDA!"
status, blob_key = client.disperse_blob(data)

if status == BlobStatus.CONFIRMED:
    print(f"Blob dispersed successfully! Key: {blob_key.hex()}")
```

### Production Client (V2) - With On-Demand Payments

For production use with on-demand payments (when you have ETH deposited in PaymentVault):

```python
# See examples/test_with_proper_payment.py for full implementation
# Key steps:

1. Get current payment state
2. Calculate payment based on blob size (min 4096 symbols)
3. Increment cumulative payment
4. Disperse blob with payment metadata
```

Working example that successfully dispersed a blob:

```bash
python examples/test_with_proper_payment.py

# Output:
# ✅ Success!
# Status: BlobStatus.PROCESSING
# Blob Key: 3aaf8a5f848e53a5ecaff30de372a5c0931468d0f46b64fcc5d3984692c0f109
# Explorer: https://blobs-v2-testnet-holesky.eigenda.xyz/blobs/...
```

### Full Client with Both Payment Methods

The client automatically detects and uses the appropriate payment method:

```python
from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.payment import PaymentConfig
from eigenda.config import get_network_config

# Get network configuration
network_config = get_network_config()

# Initialize client
client = DisperserClientV2Full(
    hostname=network_config.disperser_host,
    port=network_config.disperser_port,
    use_secure_grpc=True,
    signer=signer,
    payment_config=PaymentConfig(
        price_per_symbol=network_config.price_per_symbol,
        min_num_symbols=network_config.min_num_symbols
    )
)

# The client will automatically:
# 1. Check if you have an active reservation
# 2. Use reservation if available (cumulative_payment = empty)
# 3. Fall back to on-demand if no reservation (cumulative_payment = calculated)
```

See `examples/test_both_payments.py` for a complete example.

### Blob Retrieval

The client includes a retriever for getting blobs back from EigenDA nodes:

```python
from eigenda.retriever import BlobRetriever

# Initialize retriever
retriever = BlobRetriever(
    hostname="node.eigenda.xyz",  # EigenDA node address
    port=443,
    use_secure_grpc=True,
    signer=signer  # Optional authentication
)

# Retrieve a blob (requires blob header from dispersal)
encoded_data = retriever.retrieve_blob(
    blob_header=blob_header,        # From dispersal
    reference_block_number=12345,   # Ethereum block at dispersal time
    quorum_id=0                     # Which quorum to retrieve from
)

# Decode to get original data
from eigenda.codec.blob_codec import decode_blob_data
original_data = decode_blob_data(encoded_data)
```

**Important Notes about Retrieval:**
1. The retriever connects directly to EigenDA nodes, not the disperser
2. You need the full blob header from dispersal, not just the blob key
3. You must save the blob header and reference block when dispersing
4. The node address depends on which nodes are storing your quorum

See `examples/blob_retrieval_example.py` and `examples/dispersal_with_retrieval_support.py` for complete examples.

## Features

- **Full V2 Protocol**: Complete implementation of EigenDA v2 with gRPC
- **Authentication**: ECDSA signatures with proper key derivation
- **BN254 Compatibility**: Handles field element constraints and point compression
- **G1/G2 Decompression**: Full support for gnark-crypto compressed points
- **Type Safety**: Comprehensive type definitions matching the protocol

## Technical Details

### Payment Methods

1. **Reservation-Based** (Pre-paid bandwidth)
   - Fixed symbols/second allocation
   - No per-blob charges
   - `cumulative_payment` = empty bytes
   - Ideal for high-volume users

2. **On-Demand** (Pay per blob)
   - Requires ETH deposit in PaymentVault contract
   - Charged per blob based on size
   - `cumulative_payment` = running total in wei
   - Minimum 4096 symbols per blob

### Authentication
- Uses Keccak256 for hashing, wrapped with SHA256 for signatures
- Proper V value adjustment for Ethereum/Go compatibility
- Length-prefixed encoding for payment state requests

### Point Decompression
- G1: 32-byte compressed points with gnark flags (0x40, 0x80, 0xC0)
- G2: 64-byte compressed points with full Fp2 arithmetic
- Tonelli-Shanks algorithm adapted for quadratic extension fields

## Environment Variables

- `EIGENDA_PRIVATE_KEY`: Your Ethereum private key for signing requests (with 0x prefix)

## Development

### Project Milestones

The EigenDA Python client has achieved several significant milestones:

1. **✅ Full Protocol Implementation** - Complete v2 protocol support with all features
2. **✅ 95% Test Coverage** - Comprehensive test suite with 332 tests
3. **✅ 100% Linting Compliance** - 0 errors, fully PEP8 compliant
4. **✅ Production Ready** - Successfully dispersing blobs on mainnet and testnets

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest --cov=src --cov-report=term-missing

# Run specific test categories
pytest tests/test_client_v2_full.py  # Client tests
pytest tests/test_integration_*.py   # Integration tests

# Test Statistics:
# - Total: 332 tests (330 passing, 2 skipped)
# - Coverage: 95% (excluding generated gRPC files)
# - Files with 100% coverage: 13 out of 16
```

### Test Suite Structure

The test suite includes comprehensive unit and integration tests:

**Unit Tests:**
- `test_client_v2_full.py` - DisperserClientV2Full with payment handling
- `test_codec.py` - Blob encoding/decoding (100% coverage)
- `test_serialization.py` - Blob key calculation (100% coverage)
- `test_payment.py` - Payment calculations (98% coverage - line 42 unreachable)
- `test_g1_g2_decompression.py` - Point decompression
- `test_network_config.py` - Network configuration
- `test_mock_client.py` - Mock client (100% coverage)

**Integration Tests:**
- `test_integration_grpc.py` - Mock gRPC server integration (11 tests)
- `test_integration_e2e.py` - End-to-end workflows (11 tests)
- `test_integration_retriever.py` - Retriever integration (11 tests)

The integration tests use mock gRPC servers to test the complete flow without requiring actual network connections.

### Test Coverage Highlights

**Exceptional Coverage Achievement: 95% Overall!**

**Files with 100% Coverage** (13 out of 16 files):
- Core Components: `client.py`, `client_v2.py`, `client_v2_full.py`
- Authentication: `auth/signer.py`
- Data Processing: `codec/blob_codec.py`, `core/types.py`
- Utilities: `utils/abi_encoding.py`, `utils/serialization.py`
- Point Operations: `utils/g2_decompression.py`, `utils/gnark_decompression.py`
- Infrastructure: `config.py`, `retriever.py`, `_version.py`

**Near-Perfect Coverage**:
- `payment.py` (98% - line 42 mathematically unreachable due to formula constraints)
- `utils/fp2_arithmetic.py` (73% - complex mathematical edge cases)
- `utils/bn254_field.py` (68% - Tonelli-Shanks algorithm edge cases)

The unreachable line in `payment.py` is due to mathematical constraints: `(data_len + 30) // 31` always produces a value >= 1 for any data_len > 0.

### Running Examples

```bash
# Mock client example
python examples/minimal_client.py

# Real disperser test
python examples/test_v2_client.py
```

### Code Quality

**✅ 100% PEP8 Compliant** - The codebase has 0 linting errors!

The project maintains high code quality standards with automated tooling:

```bash
# Check code quality (0 errors!)
flake8 . --exclude="*/grpc/*" --max-line-length=127

# Tools used for automatic fixes:
autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive . --exclude "*/grpc/*"
autopep8 --in-place --max-line-length=127 --recursive . --exclude="*/grpc/*"

# Custom fixes for specific issues
python fix_linting.py  # Fixes f-strings without placeholders, trailing whitespace
```

**Linting achievements:**
- Fixed 120 total linting issues (including 2 complexity warnings)
- 0 remaining errors or warnings
- Configured with `.flake8` for consistent style
- CI/CD integration ensures ongoing compliance
- Refactored complex functions for better maintainability:
  - `check_payment_vault.py`: Reduced complexity from 11 to ~5
  - `full_example.py`: Reduced complexity from 15 to ~5

**Example files improvements:**
- Fixed import order in all example files
- Examples can now be run directly without PYTHONPATH configuration
- Proper `sys.path` setup before `eigenda` imports

### Regenerating gRPC Code

```bash
python scripts/generate_grpc.py
python scripts/fix_grpc_imports.py
```

## Requirements

- Python 3.9+
- See requirements.txt for full dependencies

## License

MIT License - Copyright (c) 2025 Powerloom

## About

This Python client for EigenDA v2 was developed by [Powerloom](https://powerloom.io/), a decentralized data protocol. For questions or support, please reach out to the Powerloom team.