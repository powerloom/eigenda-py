# EigenDA Python Client

[![PyPI version](https://badge.fury.io/py/eigenda.svg)](https://badge.fury.io/py/eigenda)
[![Python](https://img.shields.io/pypi/pyversions/eigenda.svg)](https://pypi.org/project/eigenda/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/powerloom/eigenda-py/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/powerloom/eigenda-py/actions/workflows/publish-pypi.yml)

A Python implementation of the EigenDA v2 client for interacting with the EigenDA protocol.

## Overview

This client provides a Python interface to EigenDA, a decentralized data availability service. It includes full authentication support and compatibility with the official Go and Rust implementations.

### Package Contents

The `eigenda` package includes:
- **DisperserClientV2Full** - Full-featured client with automatic payment handling
- **DisperserClientV2** - Low-level gRPC client for advanced use cases
- **MockDisperserClient** - Mock client for testing without network calls
- **BlobRetriever** - Client for retrieving dispersed blobs
- Complete type definitions and utilities for EigenDA protocol v2

## Status

✅ **Fully Working!** - The client successfully disperses blobs to EigenDA using both reservation-based and on-demand payments.

### Important Update (Latest)
**Fixed BlobStatus enum mismatch with v2 protocol** - The Python client now correctly maps blob status values to match the EigenDA v2 protobuf definition. This fixes the issue where status 0 (UNKNOWN) was being returned when blobs were actually being processed. Status values now correctly show QUEUED, ENCODED, etc.

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

## Requirements

- Python 3.9 or higher
- Ethereum private key for signing requests
- Network access to EigenDA disperser endpoints

## Installation

### From PyPI (For Users)

```bash
# Install from PyPI
pip install eigenda

# Or install from TestPyPI for pre-release versions
pip install -i https://test.pypi.org/simple/ eigenda
```

### From Source (For Development)

#### Using Poetry (Recommended)

The project uses Poetry for dependency management, which provides better dependency resolution and reproducible builds.

```bash
# Clone the repository
git clone https://github.com/powerloom/eigenda-py.git
cd eigenda-py

# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# Or install without development dependencies
poetry install --without dev

# Install with optional groups (docs, notebook)
poetry install --with docs,notebook
```

For detailed Poetry usage instructions, see our [Poetry Guide](docs/POETRY_GUIDE.md).

#### Using pip

If you prefer to use pip directly:

```bash
# Clone and install
git clone https://github.com/powerloom/eigenda-py.git
cd eigenda-py

# Export requirements from Poetry (if requirements.txt doesn't exist)
poetry export -f requirements.txt --output requirements.txt --without-hashes

# Install with pip
pip install -r requirements.txt
```

## Quick Start

### Using the Package

After installing via pip, you can use the package directly in your Python code:

```python
from eigenda import DisperserClientV2Full
from eigenda.payment import PaymentConfig
import os

# Set up payment configuration
payment_config = PaymentConfig(
    private_key=os.getenv("EIGENDA_PRIVATE_KEY"),
    network="sepolia"  # or "holesky", "mainnet"
)

# Create client
client = DisperserClientV2Full(
    host="disperser-testnet-sepolia.eigenda.xyz",
    port=443,
    use_secure_grpc=True,
    payment_config=payment_config
)

# Disperse data
data = b"Hello, EigenDA!"
blob_key = client.disperse_blob(data)
print(f"Blob key: {blob_key.hex()}")

# Check status
status = client.get_blob_status(blob_key.hex())
print(f"Status: {status}")

# Clean up
client.close()
```

### Checking Package Version

```python
import eigenda
print(eigenda.__version__)  # Output: 0.1.0
```

### Running Examples from Source

1. **Set Environment Variables**
```bash
# Create .env file
cp .env.example .env

# Add your private key
echo "EIGENDA_PRIVATE_KEY=your_private_key_here" >> .env
```

2. **Run Examples**
```bash
# Using Poetry (recommended) - no PYTHONPATH setup needed!
poetry run python examples/minimal_client.py

# Or run other examples
poetry run python examples/full_example.py
poetry run python examples/check_payment_vault.py

# Or activate the Poetry shell first
poetry shell
python examples/minimal_client.py
```

## Configuration

### Environment Variables

All configuration is done through environment variables. See [docs/ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md) for complete reference.

**Required:**
- `EIGENDA_PRIVATE_KEY` - Your Ethereum private key (without 0x prefix)

**Optional (with defaults):**
- `EIGENDA_DISPERSER_HOST` - Default: `disperser-testnet-sepolia.eigenda.xyz`
- `EIGENDA_DISPERSER_PORT` - Default: `443`
- `EIGENDA_USE_SECURE_GRPC` - Default: `true`

### Network Selection

The client automatically detects the network based on the `EIGENDA_DISPERSER_HOST` environment variable:

```bash
# Sepolia testnet (default)
EIGENDA_DISPERSER_HOST=disperser-testnet-sepolia.eigenda.xyz

# Holesky testnet
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
# Status: BlobStatus.QUEUED
# Blob Key: 3aaf8a5f848e53a5ecaff30de372a5c0931468d0f46b64fcc5d3984692c0f109
# Explorer: https://blobs-v2-testnet-holesky.eigenda.xyz/blobs/...
```

### Full Client with Both Payment Methods

The client automatically detects and uses the appropriate payment method. **Note**: The client now properly syncs payment state between blobs to handle concurrent usage:

```python
from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.payment import PaymentConfig
from eigenda.config import get_network_config
from eigenda.codec.blob_codec import encode_blob_data
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Get network config and create signer
network_config = get_network_config()
private_key = os.getenv("EIGENDA_PRIVATE_KEY")
signer = LocalBlobRequestSigner(private_key)

# Initialize client with automatic payment handling
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

# Disperse a blob - payment method is handled automatically
test_data = b"Hello EigenDA!"
encoded_data = encode_blob_data(test_data)
status, blob_key = client.disperse_blob(
    data=encoded_data,
    blob_version=0,
    quorum_ids=[0, 1]
)

print(f"Status: {status}")
print(f"Blob key: {blob_key.hex()}")
print(f"Explorer: https://blobs-v2-testnet-holesky.eigenda.xyz/blobs/{blob_key.hex()}")

# Check which payment method was used
payment_state = client.get_payment_state()
if payment_state.cumulative_payment == b'':
    print("Using reservation-based payment")
else:
    cumulative = int.from_bytes(payment_state.cumulative_payment, 'big')
    print(f"Using on-demand payment, total spent: {cumulative} wei")

client.close()
```

The client automatically:
1. Checks if you have an active reservation
2. Uses reservation if available (cumulative_payment = empty)
3. Falls back to on-demand if no reservation (cumulative_payment = calculated)
4. **Refreshes payment state before each blob** to sync with server (bug fix)

See `examples/test_both_payments.py` for a complete example.

### Checking Blob Status

After dispersing a blob, you can check its status to monitor the dispersal process:

```python
# Check status of a blob
status = client.get_blob_status(blob_key)
print(f"Status: {status.name}")

# Status values in v2 protocol:
# - UNKNOWN (0): Error or unknown state
# - QUEUED (1): Blob queued for processing
# - ENCODED (2): Blob encoded into chunks
# - GATHERING_SIGNATURES (3): Collecting node signatures
# - COMPLETE (4): Successfully dispersed
# - FAILED (5): Dispersal failed
```

See `examples/check_blob_status.py` for monitoring status until completion, or `examples/check_existing_blob_status.py` to check a specific blob key.

### Advanced Reservations (Per-Quorum Support)

The Python client now supports advanced per-quorum reservations, bringing it to feature parity with the Go client. This allows for more granular control over bandwidth allocation and payment tracking:

```python
from eigenda.client_v2_full import DisperserClientV2Full

# Enable advanced reservations
client = DisperserClientV2Full(
    hostname="disperser.eigenda.xyz",
    port=443,
    use_secure_grpc=True,
    signer=signer,
    payment_config=PaymentConfig(),
    use_advanced_reservations=True  # Enable per-quorum support
)

# The client will automatically:
# 1. Use GetPaymentStateForAllQuorums to get per-quorum reservation info
# 2. Track period records for each quorum separately
# 3. Validate reservations with nanosecond precision
# 4. Support bin-based usage tracking with overflow handling
# 5. Fall back to on-demand per quorum if needed

# Check advanced payment state
payment_state = client.get_payment_state_for_all_quorums()
if payment_state:
    for quorum_id, reservation in payment_state.quorum_reservations.items():
        print(f"Quorum {quorum_id}: {reservation.symbols_per_second} symbols/sec")
```

Key features of advanced reservations:
- **Per-quorum tracking**: Different reservations for different quorums
- **Period records**: Usage tracked in time-based bins
- **Nanosecond precision**: Matches Go client timing accuracy
- **Automatic fallback**: Seamlessly switches to on-demand when needed
- **Thread-safe**: Concurrent blob dispersals are handled correctly

Examples demonstrating reservation features:
- `examples/advanced_reservations.py` - Reservation-only dispersal (no fallback)
- `examples/test_both_payments.py` - Automatic payment method selection
- `examples/check_payment_vault.py` - Check on-chain reservation status
- `examples/debug_payment_state.py` - Debug payment configuration

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

### Development Setup

When developing or running code directly from the repository, Poetry handles the Python path automatically:

```bash
# Install the project in development mode
poetry install

# Run scripts with Poetry
poetry run python your_script.py

# Or activate the virtual environment
poetry shell
python your_script.py
```

The project is configured to use the `src/` layout, and Poetry automatically handles the import paths when you install the project.

### Project Milestones

The EigenDA Python client has achieved several significant milestones:

1. **✅ Full Protocol Implementation** - Complete v2 protocol support with all features
2. **✅ 95% Test Coverage** - Comprehensive test suite with 332 tests
3. **✅ 100% Linting Compliance** - 0 errors, fully PEP8 compliant
4. **✅ Production Ready** - Successfully dispersing blobs on mainnet and testnets
5. **✅ Modern Python Packaging** - Full Poetry support with organized dependency groups
6. **✅ Python 3.13 Support** - Compatible with Python 3.9 through 3.13

### Running Tests

```bash
# Using Poetry (recommended)
poetry run pytest tests/

# Run with coverage report
poetry run pytest --cov=src --cov-report=term-missing

# Run specific test categories
poetry run pytest tests/test_client_v2_full.py  # Client tests
poetry run pytest tests/test_integration_*.py   # Integration tests

# Or activate the virtual environment first
poetry shell
pytest tests/

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

All examples have been updated to work with the latest code changes, including proper BlobStatus enum values and correct API usage.

```bash
# Using Poetry (recommended)
poetry run python examples/test_both_payments.py

# Full example with dispersal and status monitoring
poetry run python examples/full_example.py

# Check your PaymentVault balance and pricing
poetry run python examples/check_payment_vault.py

# Check blob status after dispersal (monitors until completion)
poetry run python examples/check_blob_status.py

# Check status of an existing blob
poetry run python examples/check_existing_blob_status.py <blob_key_hex>

# Simple example with mock client
poetry run python examples/minimal_client.py
# Or activate the virtual environment first
poetry shell
python examples/test_both_payments.py
```

**Note**: All examples now properly handle the v2 protocol's status values (QUEUED, ENCODED, etc.) and use the correct API methods.

### Code Quality

**✅ 100% PEP8 Compliant** - The codebase has 0 linting errors!

The project maintains high code quality standards with automated tooling:

```bash
# Check code quality using Poetry (0 errors!)
poetry run flake8 . --exclude="*/grpc/*" --max-line-length=127

# Run linting tools for automatic fixes:
poetry run autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive . --exclude "*/grpc/*"
poetry run autopep8 --in-place --max-line-length=127 --recursive . --exclude="*/grpc/*"

# Custom fixes for specific issues
poetry run python fix_linting.py  # Fixes f-strings without placeholders, trailing whitespace

# Or use pre-commit hooks (if configured)
poetry run pre-commit run --all-files
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
- Examples work seamlessly with Poetry - no PYTHONPATH configuration needed
- Removed sys.path hacks as Poetry handles imports automatically

**Critical bug fixes:**
- Fixed on-demand payment state synchronization issue
- Client now refreshes cumulative payment from server before each blob
- Resolves "insufficient cumulative payment increment" errors when sending multiple blobs

### Regenerating gRPC Code

```bash
poetry run python scripts/generate_grpc.py
poetry run python scripts/fix_grpc_imports.py
```

## Recent Updates

### August 6th 2025
- **Default Network Changed to Sepolia**: All examples and configuration now default to Sepolia testnet
- **Standardized Environment Variables**: Consistent usage across all examples
  - `EIGENDA_PRIVATE_KEY` - Your private key  
  - `EIGENDA_DISPERSER_HOST` - Default: `disperser-testnet-sepolia.eigenda.xyz`
  - `EIGENDA_DISPERSER_PORT` - Default: `443`
  - `EIGENDA_USE_SECURE_GRPC` - Default: `true`
- **Documentation Updates**:
  - Created comprehensive `docs/ENVIRONMENT_VARIABLES.md`
  - Updated all examples to use `dotenv` for loading environment variables
  - Fixed incorrect hostnames in test files
- **Test Fixes**: Updated test fixtures to properly initialize accountant objects (all 352 tests passing)
- **Enhanced check_payment_vault.py**: Added `--address` flag to check any address without private key
- **Backward Compatible**: Holesky still supported via explicit configuration

### July 15th 2025
- **Advanced Reservation Support** (Feature Parity with Go Client):
  - Added per-quorum reservation tracking with `ReservationAccountant`
  - Implemented nanosecond timestamp precision throughout
  - Added period record tracking with bin-based usage management
  - Created comprehensive validation functions matching Go implementation
  - Added `GetPaymentStateForAllQuorums` support for per-quorum state
  - Implemented automatic fallback from reservation to on-demand per quorum
  - Added thread-safe operations with rollback capability
  - Created 22 comprehensive tests for reservation functionality
  - Added `examples/advanced_reservations.py` demonstrating new features
- **Updated Examples for Reservation Support**:
  - Enhanced `check_payment_vault.py` to show reservation status and time remaining
  - Updated `test_both_payments.py` to check for advanced reservations
  - Added reservation checking to `full_example.py`
  - All examples now use `use_advanced_reservations=True` flag
  - Examples properly handle both simple and per-quorum reservations

### July 10th 2025
- **Fixed BlobStatus enum mismatch**: Updated to match v2 protobuf values (QUEUED, ENCODED, etc.)
- **Updated all examples**: Fixed status checking, DisperserClientV2Full initialization, and API usage
- **Added status monitoring examples**: New examples for checking blob status during and after dispersal
- **Improved error handling**: Better error messages and recovery in examples
- **Code quality improvements**: 
  - Removed all `sys.path` hacks from examples (Poetry handles imports properly)
  - Moved all inline imports to top of files following Python best practices

## Requirements

- Python 3.9+
- Poetry (for dependency management)
- See `pyproject.toml` for full dependencies

## License

MIT License - Copyright (c) 2025 Powerloom

## About

This Python client for EigenDA v2 was developed by [Powerloom](https://powerloom.io/), a decentralized data protocol. For questions or support, please reach out to the Powerloom team.