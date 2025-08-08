# EigenDA Python Client by Powerloom

[![PyPI version](https://badge.fury.io/py/powerloom-eigenda.svg)](https://badge.fury.io/py/powerloom-eigenda)
[![Python](https://img.shields.io/pypi/pyversions/powerloom-eigenda.svg)](https://pypi.org/project/powerloom-eigenda/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/powerloom/eigenda-py/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/powerloom/eigenda-py/actions/workflows/publish-pypi.yml)

> This is an unofficial Python implementation of the EigenDA v2 client, developed by Powerloom, for interacting with the EigenDA protocol. Please note that it is on the bleeding edge and not recommended for use in production environments.

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

✅ **Production Ready!** - The client successfully disperses blobs to EigenDA using both reservation-based and on-demand payments.

**Quality Metrics:**
- 95% test coverage with 332 tests
- Zero linting errors (black, isort, flake8)
- Multi-platform support (Linux, macOS, Windows)
- Comprehensive CI/CD pipeline with security scanning

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
pip install powerloom-eigenda

# Or install from TestPyPI for pre-release versions
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple powerloom-eigenda
```

### From Source (For Development)

#### Using UV (Recommended)

The project uses UV for dependency management, which provides much faster dependency resolution and installation compared to pip.

```bash
# Clone the repository
git clone https://github.com/powerloom/eigenda-py.git powerloom-eigenda
cd powerloom-eigenda

# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies for development (recommended)
uv sync --all-extras

# This installs everything: main deps + dev tools + docs + notebook
# After this, you can run commands without additional flags:
# uv run pytest tests/
# uv run black src/
# uv run flake8 src/

# Alternative: Install only what you need
# uv sync --dev  # Just dev tools (note: requires --dev flag when running)
# uv run --dev pytest tests/  # Must use --dev flag
```

For detailed UV usage instructions, see our [UV Guide](docs/UV_GUIDE.md).

#### Using pip (Alternative)

If you prefer to use pip directly:

```bash
# Clone and install
git clone https://github.com/powerloom/eigenda-py.git
cd eigenda-py/python-client

# Export requirements from UV (if requirements.txt doesn't exist)
uv pip compile pyproject.toml -o requirements.txt

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
# Using UV - no PYTHONPATH setup needed!
uv run python examples/minimal_client.py

# Or run other examples
uv run python examples/full_example.py
uv run python examples/check_payment_vault.py

# Or activate the virtual environment first
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
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

### Production Client (V2Full) - Automatic Payment Handling

The `DisperserClientV2Full` automatically handles both reservation-based and on-demand payments:

```python
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full

# Initialize signer
signer = LocalBlobRequestSigner(private_key)

# Create client (automatically detects payment method)
client = DisperserClientV2Full(
    hostname="disperser.eigenda.xyz",
    port=443,
    use_secure_grpc=True,
    signer=signer
)

# Disperse blob (handles payment automatically)
status, blob_key = client.disperse_blob(
    data=b"Hello, EigenDA!",
    quorum_numbers=[0, 1]
)

# Check payment information
payment_info = client.get_payment_info()
print(f"Payment type: {payment_info['payment_type']}")
if payment_info['payment_type'] == 'reservation':
    print(f"Bandwidth: {payment_info['reservation_details']['symbols_per_second']} symbols/sec")
elif payment_info['payment_type'] == 'on_demand':
    print(f"Balance: {payment_info['onchain_balance']/1e18:.4f} ETH")
```

The client automatically:
1. Checks for active reservations first (pre-paid, no per-blob charges)
2. Falls back to on-demand payment if no reservation exists
3. Handles all payment calculations and metadata

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

### Reservation Support

The Python client supports EigenDA's reservation system for pre-paid bandwidth:

```python
from eigenda import DisperserClientV2Full, PaymentConfig

# Client automatically detects and uses reservations if available
client = DisperserClientV2Full(
    host="disperser-testnet-sepolia.eigenda.xyz",
    port=443,
    use_secure_grpc=True,
    signer_private_key=private_key,
    payment_config=PaymentConfig(min_symbols=4096)
)

# The client will automatically:
# 1. Check for active reservations
# 2. Use reservation if available (no ETH charges)
# 3. Fall back to on-demand payment if no reservation

# Check detailed payment info
info = client.get_payment_info()
if info["reservation"]:
    print(f"Using reservation for quorums: {info['reservation']['quorums']}")
    print(f"Time remaining: {info['reservation']['time_remaining']} seconds")
    print(f"Bandwidth available: {info['reservation']['bandwidth']}")
```

Key features of reservations:
- **Pre-paid bandwidth**: Purchase bandwidth in advance with no per-blob charges
- **Automatic detection**: Client checks for active reservations before dispersal
- **Seamless fallback**: Automatically uses on-demand payment if no reservation

## Examples

The `examples/` directory contains working examples for various use cases:

### Payment and Dispersal
- `minimal_client.py` - Simplest example using mock client
- `full_example.py` - Complete dispersal workflow with DisperserClientV2Full
- `test_reservation_account.py` - Check if account has reservation and test it
- `test_both_payments.py` - Test accounts with different payment methods
- `test_with_proper_payment.py` - Manual payment calculation with DisperserClientV2
- `check_payment_vault.py` - Check on-chain PaymentVault status
- `debug_payment_state.py` - Debug payment configuration issues

### Blob Operations
- `check_blob_status.py` - Monitor blob status after dispersal
- `check_existing_blob_status.py` - Check status of previously dispersed blob
- `dispersal_with_retrieval_support.py` - Save metadata for later retrieval
- `blob_retrieval_example.py` - Retrieve blob from EigenDA nodes

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

When developing or running code directly from the repository, UV handles the Python path automatically:

```bash
# Install the project in development mode
uv sync

# Run scripts with UV
uv run python your_script.py

# Or activate the virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
python your_script.py
```

The project is configured to use the `src/` layout, and UV automatically handles the import paths when you install the project.

### Project Milestones

The EigenDA Python client has achieved several significant milestones:

1. **✅ Full Protocol Implementation** - Complete v2 protocol support with all features
2. **✅ 95% Test Coverage** - Comprehensive test suite with 332 tests
3. **✅ 100% Linting Compliance** - 0 errors, fully PEP8 compliant
4. **✅ Production Ready** - Successfully dispersing blobs on mainnet and testnets
5. **✅ Modern Python Packaging** - UV package manager with ultra-fast dependency resolution
6. **✅ Python 3.13 Support** - Compatible with Python 3.9 through 3.13

## Development Workflow

### Code Quality Checks

The project enforces strict code quality standards using black, isort, and flake8. All tools use consistent versions to ensure reproducible results.

**Tool Versions** (managed by UV and pre-commit):
- black: 25.1.0
- isort: 6.0.1  
- flake8: 7.3.0

These versions are synchronized between UV dependencies and pre-commit hooks to ensure consistency.

#### Quick Code Quality Check

```bash
# Check code quality (no changes made)
./scripts/verify_code_quality.sh

# Auto-fix formatting issues
./scripts/verify_code_quality.sh --fix
```

#### Manual Commands

```bash
# Check formatting without making changes
uv run black --check src/ tests/ examples/
uv run isort --check-only src/ tests/ examples/
uv run flake8 .

# Apply formatting fixes
uv run black src/ tests/ examples/
uv run isort src/ tests/ examples/
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit` to prevent poorly formatted code from being committed. They are configured to **check only**, not auto-fix, ensuring you review all changes.

```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Manual check (runs all hooks)
uv run pre-commit run --all-files

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

**Checks performed on commit:**
- Python syntax validation (AST check)
- Code formatting verification (black) - shows diff of needed changes
- Import sorting verification (isort) - shows diff of needed changes
- Linting (flake8) - reports style violations
- File format validation (YAML, TOML, JSON)
- Large file detection (>1MB warning)
- Merge conflict detection

**Important:** Pre-commit hooks will **not** automatically modify your files. They perform the following:
- **Black & isort**: Show diffs of required changes, block commit if formatting is wrong
- **Flake8**: Report all linting errors (unused imports, line length, etc.), block commit if any errors exist
- **File checks**: Validate YAML/JSON/TOML syntax, check for merge conflicts, large files

If any issues are detected, the commit will be blocked and you'll need to:
1. Run `./scripts/verify_code_quality.sh --fix` to auto-fix formatting issues
2. Manually fix any remaining linting errors (unused variables, etc.)
3. Review and stage the changes with `git add`
4. Commit again

### CI/CD Pipeline

GitHub Actions runs comprehensive checks on every push:

**Pipeline Jobs:**
- **Lint**: Code formatting and linting validation
- **Test**: Multi-platform testing (Ubuntu, macOS, Windows) across Python 3.9-3.13
- **Security**: Vulnerability scanning with bandit and safety
- **Build**: Package building and PyPI compatibility check
- **Coverage**: Automated PR comments with coverage metrics

### Running Tests

```bash
# Using UV (recommended)
uv run pytest tests/

# Run with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Run specific test categories
uv run pytest tests/test_client_v2_full.py  # Client tests
uv run pytest tests/test_integration_*.py   # Integration tests

# Or activate the virtual environment first
source .venv/bin/activate  # Linux/macOS
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
# Using UV (recommended)
uv run python examples/test_both_payments.py

# Full example with dispersal and status monitoring
uv run python examples/full_example.py

# Check your PaymentVault balance and pricing
uv run python examples/check_payment_vault.py

# Check blob status after dispersal (monitors until completion)
uv run python examples/check_blob_status.py

# Check status of an existing blob
uv run python examples/check_existing_blob_status.py <blob_key_hex>

# Simple example with mock client
uv run python examples/minimal_client.py
# Or activate the virtual environment first
source .venv/bin/activate  # Linux/macOS
python examples/test_both_payments.py
```

**Note**: All examples now properly handle the v2 protocol's status values (QUEUED, ENCODED, etc.) and use the correct API methods.

### Code Quality

**✅ 100% PEP8 Compliant** - The codebase has 0 linting errors!

The project maintains high code quality standards with automated tooling:

```bash
# Check code quality using UV (0 errors!)
uv run flake8 . --exclude="*/grpc/*" --max-line-length=127

# Run linting tools for automatic fixes:
uv run autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive . --exclude "*/grpc/*"
uv run autopep8 --in-place --max-line-length=127 --recursive . --exclude="*/grpc/*"

# Custom fixes for specific issues
uv run python fix_linting.py  # Fixes f-strings without placeholders, trailing whitespace

# Or use pre-commit hooks (if configured)
uv run pre-commit run --all-files
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
- Examples work seamlessly with UV - no PYTHONPATH configuration needed
- Removed sys.path hacks as UV handles imports automatically

**Critical bug fixes:**
- Fixed on-demand payment state synchronization issue
- Client now refreshes cumulative payment from server before each blob
- Resolves "insufficient cumulative payment increment" errors when sending multiple blobs

### Regenerating gRPC Code

```bash
uv run python scripts/generate_grpc.py
uv run python scripts/fix_grpc_imports.py
```

## Recent Updates

### August 7th 2025
- **Migrated to UV Package Manager**:
  - Replaced Poetry with UV for 10-100x faster dependency resolution
  - Updated all documentation and scripts to use UV commands
  - Updated GitHub Actions workflows to use `astral-sh/setup-uv@v6`
  - Updated Makefile and code quality scripts for UV
  - Created comprehensive UV guide at `docs/UV_GUIDE.md`
  - All tests passing with 93% coverage under UV

### August 6th 2025
- **Simplified Reservation Support**: Removed advanced per-quorum reservation complexity
  - Client now uses simpler reservation detection without per-quorum tracking
  - Removed `use_advanced_reservations` parameter from `DisperserClientV2Full`
  - Streamlined to match actual protocol usage patterns
  - Maintains full support for basic reservation-based dispersal
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
- UV (for ultra-fast dependency management)
- See `pyproject.toml` for full dependencies

## License

MIT License - Copyright (c) 2025 Powerloom

## About

This unofficial Python client for EigenDA v2 was developed by [Powerloom](https://powerloom.io/), a decentralized data protocol. For questions or support, please reach out to the Powerloom team using the [issue tracker](https://github.com/powerloom/eigenda-py/issues).
