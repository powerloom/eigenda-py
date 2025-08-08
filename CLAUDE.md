# EigenDA Python Client - Development Notes

This document contains important implementation details and context for the EigenDA Python client.

## Project Overview

The Python client provides full Python support for EigenDA v2, with feature parity to the reference implementations in Go and Rust. The package is published to PyPI as `powerloom-eigenda`.

## Project Structure

The project now uses UV and follows a standard Python package structure with `src/` layout:

- `src/eigenda/` - Main package with client implementation
  - `client.py` - Mock client for basic testing (fully working)
  - `client_v2.py` - Full gRPC v2 client (fully working)
  - `client_v2_full.py` - Extended client with automatic payment handling
  - `auth/signer.py` - ECDSA signing implementation
  - `codec/blob_codec.py` - Data encoding/decoding
  - `core/types.py` - Core type definitions
  - `utils/serialization.py` - Blob key calculation (fully working)
  - `payment.py` - Payment calculation and accountant classes
  - `config.py` - Network configuration management
  - `retriever.py` - Blob retrieval implementation
- `src/eigenda/grpc/` - Generated gRPC stubs from proto files
- `examples/` - Example scripts demonstrating usage
  - `minimal_client.py` - Works with mock client
  - `test_v2_client.py` - Tests real gRPC (fully working)
  - `full_example.py` - Complete dispersal/retrieval example
  - `test_reservation_account.py` - Reservation detection and testing
  - `test_both_payments.py` - Tests both payment methods
  - `check_payment_vault.py` - Check PaymentVault contract state
  - `check_blob_status.py` - Monitor blob dispersal progress
  - `check_existing_blob_status.py` - Check status of existing blobs
- `tests/` - Comprehensive test suite with 95% coverage (332 tests)
- `scripts/` - Utility scripts for gRPC generation
  - `generate_grpc.py` - Generates Python code from protos
  - `fix_grpc_imports.py` - Fixes import issues in generated code

## Key Implementation Details

### 1. gRPC Code Generation

The gRPC stubs are generated from proto files using:
```bash
python scripts/generate_grpc.py
```

Common issues with generated files:
- Double imports like `from eigenda.grpc.common import eigenda.grpc.common_pb2`
- Fixed by running `python scripts/fix_grpc_imports.py`

### 2. Authentication & Signing

The EigenDA v2 protocol requires ECDSA signatures for authentication:

- Uses `eth_account` library for signing
- The `unsafe_sign_hash` method is used for raw hash signing (not `signHash`)
- Signatures must be in the format: r(32) + s(32) + v(1) = 65 bytes total
- The blob key is signed directly without any message prefix

### 3. Payment Header

The PaymentHeader requires:
- `account_id`: Ethereum address as string (with 0x prefix)
- `timestamp`: Unix timestamp in nanoseconds (int64)
- `cumulative_payment`: Empty bytes for reservation-based, or serialized uint256 for on-demand

### 4. Data Encoding

Data must be encoded before dispersal:
- Uses `encode_blob_data()` which adds padding bytes
- Every 31 bytes of data gets a 0x00 prefix byte
- Ensures data stays within valid BN254 field element range

### 5. Current Status

✅ **All features fully implemented and working:**
- ✅ Basic client structure implemented
- ✅ gRPC communication working
- ✅ Data encoding/decoding implemented
- ✅ Mock DisperserClient for testing
- ✅ Full DisperserClientV2 with gRPC
- ✅ Signature verification working (fixed recovery ID)
- ✅ Payment state authentication working
- ✅ Blob dispersal to mainnet and testnets
- ✅ Both payment methods (reservation and on-demand)

### 6. Testing

To test the client:
1. Set `EIGENDA_PRIVATE_KEY` environment variable
2. Run `python examples/minimal_client.py` (uses mock client)
3. Run `python examples/test_v2_client.py` (uses real gRPC)

### 7. Testing Status

**Test Coverage**: 95% (excluding generated gRPC files) 🎉
- 332 tests total (330 passing, 2 skipped)
- Comprehensive test suites including:
  - Unit tests for all core components
  - Integration tests with mock gRPC servers
  - End-to-end workflow tests
  - Performance and error handling tests
  - Complete mock client test coverage

**Test Suite Organization**:

**Unit Tests** (178 tests):
- `test_client_v2_full.py` - DisperserClientV2Full with payment handling
- `test_codec.py` - Blob encoding/decoding
- `test_serialization.py` - Blob key calculation
- `test_payment.py` - Payment calculations
- `test_g1_g2_decompression.py` - Point decompression
- `test_network_config.py` - Network configuration
- `test_retriever.py` - Basic retriever tests
- `test_mock_client.py` - Comprehensive mock client tests (17 tests)
- Additional unit tests for auth, types, and utilities

**Integration Tests** (33 tests):
- `test_integration_grpc.py` - Mock gRPC server integration (11 tests)
  - Full dispersal flow with real gRPC
  - Payment state retrieval
  - Blob status polling
  - Concurrent operations
  - Error handling
- `test_integration_e2e.py` - End-to-end workflows (11 tests)
  - Complete dispersal flow
  - Payment calculation flow
  - Network configuration integration
  - Signature verification
  - Performance tests
- `test_integration_retriever.py` - Retriever integration (11 tests)
  - Blob retrieval with mock server
  - Error scenarios
  - Concurrent retrieval
  - Performance tests

**Key Component Coverage** (excluding generated files):
- **100% Coverage (13 files)**: ✨
  - `client.py`, `client_v2.py`, `client_v2_full.py` - All client implementations
  - `auth/signer.py` - ECDSA signing
  - `codec/blob_codec.py` - Blob encoding/decoding
  - `config.py` - Network configuration
  - `core/types.py` - Type definitions
  - `retriever.py` - Blob retrieval
  - `utils/abi_encoding.py` - ABI encoding
  - `utils/g2_decompression.py` - G2 point operations
  - `utils/gnark_decompression.py` - Gnark compatibility
  - `utils/serialization.py` - Blob key calculation
  - `_version.py` - Version info
- **Near-Perfect Coverage**:
  - `payment.py`: 98% coverage (line 42 unreachable)
  - `utils/fp2_arithmetic.py`: 73% coverage
  - `utils/bn254_field.py`: 68% coverage

### 8. Known Issues and Progress

1. **Signature Recovery**: ✅ FIXED - The v value adjustment (v-27) resolved the recovery ID issue

2. **G1 Point Decompression**: ✅ FIXED - Implemented gnark-crypto compatible decompression
   - Gnark uses compression flags in MSB: 0x40 (infinity), 0x80 (smaller y), 0xC0 (larger y)
   - Successfully decompress G1 commitment points from 32 bytes to full (x,y) coordinates

3. **Blob Key Calculation**: ✅ FIXED - Full implementation working
   - ABI encoding structure matches Go implementation exactly
   - Payment metadata hashing implemented correctly
   - G2 Y-coordinates computed via decompression

4. **G2 Point Decompression**: ✅ FIXED - Full implementation working
   - Implemented complete Fp2 arithmetic (quadratic extension field)
   - Adapted Tonelli-Shanks algorithm for Fp2 square roots
   - Compressed format is 64 bytes (x0, x1) with compression flag
   - Successfully computes (y0, y1) from (x0, x1)

5. **Payment State Authentication**: ✅ FIXED - Working correctly
   - Must wrap Keccak256 hash with SHA256 (discovered from Go/Rust code)
   - Proper length prefixing for account bytes
   - Correct timestamp encoding

6. **Dual Payment Support**: ✅ IMPLEMENTED - Both methods working
   - Reservation-based: Empty cumulative_payment for pre-paid bandwidth
   - On-demand: Calculated cumulative_payment based on blob size
   - Automatic detection and fallback mechanism
   - Matches Go client behavior exactly

### 9. Dependencies

The project uses UV for dependency management with the following structure:

**Core Dependencies:**
- `grpcio` and `grpcio-tools` for gRPC
- `web3` and `eth-account` for Ethereum functionality
- `protobuf` for message serialization
- `cryptography` and `pycryptodome` for cryptographic operations
- `python-dotenv` for environment variable management
- Python 3.9+ required

**Development Dependencies** (in separate groups):
- `dev` group: Testing (pytest), linting (flake8, pylint), formatting (black, isort), type checking (mypy)
- `docs` group (optional): Sphinx documentation tools
- `notebook` group (optional): Jupyter and IPython for interactive development

### 10. Environment Setup

#### Using UV (Recommended)

The project uses UV for ultra-fast dependency management. UV provides 10-100x faster dependency resolution and installation compared to pip.

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Navigate to the project directory
cd eigenda-py/python-client

# Install all dependencies for development (recommended)
uv sync --all-extras

# This installs everything: main deps + dev tools + docs + notebook
# After this, you can run commands without additional flags:
uv run pytest tests/
uv run python examples/minimal_client.py

# Alternative: Install only what you need
# uv sync --dev  # Just dev tools (requires --dev flag when running)
# uv run --dev pytest tests/  # Must use --dev flag with commands
```

#### Using a specific Python version with UV

```bash
# UV can manage Python versions directly
uv sync --python 3.11

# Or run with specific version
uv run --python 3.11 python examples/minimal_client.py
```

#### Legacy pip setup (alternative)

If you need to use pip directly:
```bash
# Export requirements from UV
uv pip compile pyproject.toml -o requirements.txt

# Install with pip
pip install -r requirements.txt
```

Note: The .env file defaults to Holesky testnet. To use Sepolia, uncomment the EIGENDA_DISPERSER_HOST line.

## PyPI Publishing

The package is published to PyPI as `powerloom-eigenda` and can be installed with:

```bash
pip install powerloom-eigenda
```

### Publishing Workflow

The project uses GitHub Actions for automated publishing:
- **TestPyPI**: Publishes on pushes to `develop` branch and pull requests to `master`/`main`
  - Automatically generates dev versions with timestamps and PR numbers
- **PyPI**: Publishes on version tags (`v*`) and GitHub releases
- Uses trusted publishing (OIDC) - no API tokens needed in secrets

### Package Configuration

- **Package name**: `powerloom-eigenda`
- **Version management**: Manual versioning in pyproject.toml
  - Dev versions for TestPyPI: `0.1.0.dev<timestamp><PR_number>`
  - Production versions from git tags
- **Build system**: Hatchling with standard PEP 621 format
- **Python support**: 3.9 - 3.13

## Project Status

The EigenDA Python client v2 is now **fully functional** and ready for production use. All core features have been implemented:

1. ✅ **Complete Authentication** - ECDSA signatures with proper key derivation
2. ✅ **Blob Dispersal** - Full gRPC v2 protocol support
3. ✅ **Dual Payment Methods** - Both reservation-based and on-demand payments
4. ✅ **Network Configuration** - Automatic detection for Sepolia, Holesky, and Mainnet
5. ✅ **G1/G2 Point Decompression** - Native Python implementation matching gnark-crypto
6. ✅ **Blob Retrieval** - Basic implementation (requires relay endpoints)
7. ✅ **Clean API** - DisperserClientV2Full handles all payment complexity
8. ✅ **Comprehensive Tests** - 88% test coverage with 211 tests

## Test Suite Summary

The project now has a comprehensive test suite:
- **Total Tests**: 211 (209 passing, 2 skipped)
- **Test Coverage**: 88% (excluding generated gRPC files)
- **Test Organization**:
  - 178 unit tests covering core functionality
  - 33 integration tests with mock gRPC servers
  - Tests run without network dependencies

- **Key Areas Tested**:
  - Client creation and configuration
  - Payment state management (reservation and on-demand)
  - Blob header creation with proper payment metadata
  - Blob dispersal with automatic payment fallback
  - Serialization and blob key calculation
  - Payment metadata hashing
  - Network configuration detection
  - Payment calculations and accountant logic
  - G1/G2 point decompression
  - ECDSA signing and authentication
  - Blob retrieval from EigenDA nodes
  - gRPC connection management
  - Context manager patterns
  - Mock gRPC server interactions
  - End-to-end workflows
  - Concurrent operations
  - Error recovery scenarios
  - Performance with large blobs

## Integration Tests Added

The project now includes comprehensive integration tests that verify the complete flow:

1. **Mock gRPC Server Tests** (`test_integration_grpc.py`)
   - Real gRPC server instances for testing
   - Full protocol flow validation
   - Concurrent operation testing
   - Retry mechanism patterns

2. **End-to-End Tests** (`test_integration_e2e.py`)
   - Complete dispersal workflows
   - Payment calculation verification
   - Network configuration integration
   - Performance testing with large blobs

3. **Retriever Integration** (`test_integration_retriever.py`)
   - Blob retrieval with mock servers
   - Error handling scenarios
   - Concurrent retrieval operations

## Future Enhancements (Optional)

1. ~~Add integration tests with real gRPC server~~ ✅ COMPLETED
2. Implement local KZG commitment calculation
3. Add more relay endpoints for blob retrieval
4. Performance optimizations for large blobs
5. Add streaming support for large blob operations

## Network Configuration

The client supports multiple networks with automatic detection:

1. **Network Detection**: Based on `EIGENDA_DISPERSER_HOST` environment variable
   - Sepolia: `disperser-testnet-sepolia.eigenda.xyz`
   - Holesky: `disperser-testnet-holesky.eigenda.xyz` (default)
   - Mainnet: `disperser.eigenda.xyz`

2. **PaymentVault Contracts**:
   - Sepolia: `0x2E1BDB221E7D6bD9B7b2365208d41A5FD70b24Ed`
   - Holesky: `0x4a7Fff191BCDa5806f1Bc8689afc1417c08C61AB`
   - Mainnet: `0xb2e7ef419a2A399472ae22ef5cFcCb8bE97A4B05`
   - All networks use the same pricing: 447 gwei per symbol, 4,096 minimum symbols

3. **Configuration Module**: `src/eigenda/config.py` centralizes network settings

## Working Examples

Successfully dispersed blobs on both testnets:
- Holesky Blob: `3aaf8a5f848e53a5ecaff30de372a5c0931468d0f46b64fcc5d3984692c0f109`
- Sepolia Blob: `95ae8a8aa08fec0354f439eef31b351da97972916f0bb1c8b4ff8e50a82dc080`

Key discoveries made during development:
- Must use SHA256(Keccak256(...)) for payment state authentication
- On-demand payment requires calculating cost based on blob size (min 4096 symbols)
- Price per symbol: 447 gwei (same across all networks)
- V value in signatures needs adjustment: Ethereum uses 27/28, Go expects 0/1
- G2 points use quadratic extension field Fp2 for decompression

## Recent Updates

### Development Workflow Enhancements (August 6th 2025)

1. **Pre-commit Hooks Configured (Check-Only Mode)**:
   - Runs black, isort, and flake8 on every git commit
   - **Check-only mode**: Prevents commits with issues but doesn't auto-fix
   - Manual fix option via `./scripts/verify_code_quality.sh --fix`
   - Version-synchronized tools between UV and pre-commit:
     - black: 25.1.0 (100 char line length)
     - isort: 6.0.1 (black compatibility)
     - flake8: 7.3.0 (configured for black compatibility)
   - Configuration in `.pre-commit-config.yaml`
   - Install with: `uv run pre-commit install`

2. **Code Quality Verification Script**:
   - Located at `scripts/verify_code_quality.sh`
   - Default mode: Checks code quality without modifications
   - Fix mode (`--fix` or `-f` flag): Auto-formats code
   - Provides developer control over when to apply fixes
   - Example usage:
     ```bash
     # Check only (no modifications)
     ./scripts/verify_code_quality.sh
     
     # Auto-fix formatting issues
     ./scripts/verify_code_quality.sh --fix
     ```

3. **Enhanced GitHub Actions Workflow**:
   - Separated jobs for lint, test, security, build, and coverage
   - Multi-platform testing (Ubuntu, macOS, Windows)
   - Python 3.9-3.13 support
   - Security scanning with bandit and safety
   - Automatic PR comments with coverage metrics
   - Build validation with twine

4. **Code Quality Improvements**:
   - All files pass black formatting (100 char line length)
   - All imports properly sorted with isort
   - Zero flake8 linting errors (E203, W503 ignored for black compatibility)
   - 95% test coverage maintained
   - Tool versions synchronized between UV dependencies and pre-commit hooks

### Example Files Fixed and Enhanced (August 6th 2025)
All example files have been updated for compatibility with the latest code changes:

1. **Fixed parameter inconsistencies**:
   - `DisperserClientV2` uses `quorum_ids` parameter
   - `DisperserClientV2Full` uses `quorum_numbers` parameter
   - `MockDisperserClient` uses `quorum_numbers` parameter

2. **Fixed status parsing in examples**:
   - `check_existing_blob_status.py` - Now correctly parses BlobStatus from protobuf response
   - `check_blob_status.py` - Already had correct status parsing
   - `dispersal_with_retrieval_support.py` - Fixed BlobStatus.PROCESSING → BlobStatus.QUEUED

3. **Added `get_payment_info()` method to DisperserClientV2Full**:
   - Returns comprehensive payment information including:
     - Payment type (reservation/on_demand/none)
     - Reservation details (bandwidth, expiry, quorums, time remaining)
     - Current cumulative payment and onchain balance
     - Pricing configuration
   - Updated test coverage for the new method

4. **New reservation example**:
   - Created `test_reservation_account.py` - Working example that detects and uses reservations
   - Shows detailed reservation info (bandwidth, expiry, allowed quorums)
   - Demonstrates blob dispersal with reservation (no ETH charges)
   - Verifies that cumulative payment doesn't increase
   - Removed old `demo_reservation.py` which was just theoretical

5. **Fixed `test_both_payments.py`**:
   - Updated to use new `get_payment_info()` method
   - Checks for reservations first (matching protocol priority)
   - Shows appropriate details for each payment type

## Recent Updates

### PyPI Publishing Support Added (August 6th 2025)
The Python client is now ready for publication to PyPI as the `eigenda` package:

1. **Package Renamed**: Changed from `eigenda-py` to `eigenda` for simpler installation
2. **GitHub Actions Workflow**: Added automated publishing pipeline
   - TestPyPI for development releases (`develop` branch)
   - PyPI for stable releases (version tags)
   - Uses trusted publishing (OIDC) for secure deployment
3. **Package Building**: UV builds packages using Hatchling backend with PEP 621 format
4. **Installation**: Users can now install with `pip install powerloom-eigenda`

### Default Network Changed to Sepolia (August 6th 2025)
The Python client now uses **Sepolia testnet as the default** instead of Holesky:

1. **Configuration Changes**: Default network is now Sepolia throughout the codebase
2. **Environment Variables**: Standardized across all examples
   - `EIGENDA_PRIVATE_KEY` - Your private key
   - `EIGENDA_DISPERSER_HOST` - Default: `disperser-testnet-sepolia.eigenda.xyz`
   - `EIGENDA_DISPERSER_PORT` - Default: `443`
   - `EIGENDA_USE_SECURE_GRPC` - Default: `true`
3. **Examples Updated**: All examples now use consistent environment variables
4. **Documentation**: Created `docs/ENVIRONMENT_VARIABLES.md` for complete reference
5. **Backward Compatible**: Holesky still supported via explicit configuration

To use Holesky testnet, set: `EIGENDA_DISPERSER_HOST=disperser-testnet-holesky.eigenda.xyz`

### Enhanced check_payment_vault.py Script (August 6th 2025)
Added `--address` flag to allow checking any Ethereum address without needing the private key:

```bash
# Check your own account (requires EIGENDA_PRIVATE_KEY)
uv run python examples/check_payment_vault.py

# Check any address without private key (read-only)
uv run python examples/check_payment_vault.py --address 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0

# Short form
uv run python examples/check_payment_vault.py -a 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
```

This is useful for:
- Checking other users' payment vault status
- Debugging without exposing private keys
- Monitoring accounts programmatically
- Quick lookups of any address on-chain

### Test Failures Fixed (August 6th 2025)
Fixed failing tests related to the `accountant` attribute initialization in test fixtures:
- Updated test fixtures to properly initialize `SimpleAccountant`
- All 352 tests now pass with 92% code coverage

### Advanced Reservation Support (July 15th 2025)
The Python client now has feature parity with the Go client for reservation handling:

1. **Per-Quorum Reservations**: Full support for different reservations per quorum
2. **Period Record Tracking**: Bin-based usage tracking with circular buffer implementation
3. **Nanosecond Precision**: All timestamps now use nanoseconds matching Go client
4. **Advanced Validation**: Complete reservation validation logic ported from Go
5. **ReservationAccountant**: New accountant class handling both reservation and on-demand
6. **GetPaymentStateForAllQuorums**: Support for the new gRPC method
7. **Automatic Fallback**: Seamless switching between reservation and on-demand per quorum
8. **Thread Safety**: All operations are thread-safe with proper locking
9. **Comprehensive Tests**: 22 tests covering all reservation functionality

Key files added/modified:
- `src/eigenda/core/meterer.py` - Time utilities and validation functions
- `src/eigenda/core/types.py` - Added reservation-related types
- `src/eigenda/payment.py` - Added ReservationAccountant class
- `src/eigenda/client_v2_full.py` - Updated to support per-quorum reservations
- `tests/test_reservation_parity.py` - Comprehensive test suite
- `examples/advanced_reservations.py` - Example demonstrating new features

Examples updated for reservation support:
- `check_payment_vault.py` - Shows reservation status, time remaining, human-readable timestamps
- `test_both_payments.py` - Checks for advanced reservations, shows payment method selection
- `full_example.py` - Added reservation checking before dispersal
- `debug_payment_state.py` - Checks both simple and advanced payment states

Key implementation details:
- The client supports both simple (global) and advanced (per-quorum) reservations
- Use `use_advanced_reservations=True` when creating DisperserClientV2Full
- Client automatically falls back: advanced → simple → on-demand
- Period records track usage in 3-bin circular buffer with overflow support

Comparison with other clients:
- **Go client**: Uses GetPaymentStateForAllQuorums (advanced reservations)
- **Rust client**: Uses GetPaymentState (simple reservations only)
- **Python client**: Supports BOTH approaches for maximum compatibility

### UV Package Manager Migration (August 2025)
- **Migrated to UV**: Project now uses UV for ultra-fast dependency management
- **Performance improvements**: 10-100x faster dependency resolution and installation
- **Organized dependencies**: Split into separate groups (dev, docs, notebook) for better control
- **Updated metadata**: Standard PEP 621 pyproject.toml format
- **Python 3.13 support**: Added support for latest Python version
- **Simplified workflow**: UV automatically manages virtual environments in .venv
- **Enhanced documentation**: Added comprehensive UV guide at `docs/UV_GUIDE.md`

### Integration Tests Added (older)
- Added 33 comprehensive integration tests with mock gRPC servers
- Tests cover full dispersal flow, payment handling, error scenarios, and performance
- All tests pass without requiring network connections
- Fixed minor compatibility issues in examples (minimal_client.py import)

### Mock Client Tests Added
- Added 17 comprehensive tests for the mock DisperserClient
- Achieved 100% code coverage for the mock client
- Tests cover all functionality including connection management, blob dispersal, and edge cases
- Overall test coverage improved from 85% to 88%

### Test Coverage Milestone - 95% Overall Coverage! (older)
- Achieved **100% coverage** for 13 out of 16 source files!
- Files with 100% coverage:
  - `auth/signer.py` - Complete ECDSA signing implementation
  - `client.py` - Mock client for testing
  - `client_v2.py` - Full gRPC v2 client
  - `client_v2_full.py` - Client with payment handling
  - `codec/blob_codec.py` - Data encoding/decoding
  - `config.py` - Network configuration
  - `core/types.py` - Core type definitions
  - `retriever.py` - Blob retrieval implementation
  - `utils/abi_encoding.py` - ABI encoding utilities
  - `utils/g2_decompression.py` - G2 point decompression
  - `utils/gnark_decompression.py` - Gnark-compatible decompression
  - `utils/serialization.py` - Blob key calculation
  - `_version.py` - Version information
- Near-perfect coverage:
  - `payment.py` - 98% (line 42 mathematically unreachable due to formula constraints)
  - `utils/fp2_arithmetic.py` - 73% (complex mathematical edge cases)
  - `utils/bn254_field.py` - 68% (Tonelli-Shanks algorithm edge cases)
- Overall project coverage: **95%** (832 statements, 41 missing)
- All 330 tests passing (2 skipped)

### Code Quality Improvements - 100% Linting Compliance! (older)
- **Achieved 0 linting errors** (down from 118 initially)
- Fixed all linting issues systematically:
  - **68 files** with f-strings without placeholders (F541 errors) - removed unnecessary f-string prefixes
  - **41 long lines** (E501) - split lines to stay within 100 character limit
  - **24 trailing whitespace** (W293/W291) - removed all trailing spaces
  - **5 unused variables** (F841) - removed unused assignments
  - **2 indentation issues** (E129) - fixed visual indentation
  - **1 bare except** (E722) - changed to `except Exception`
  - **1 syntax error** (E999) - fixed invalid hex escape sequence
  - **2 complexity warnings** (C901) - refactored complex functions:
    - `check_payment_vault.py`: Reduced complexity from 11 to ~5 by extracting helper functions
    - `full_example.py`: Reduced complexity from 15 to ~5 by modularizing the workflow
- Tools and configuration:
  - Created custom linting fix script: `fix_linting.py`
  - Configured flake8 with `.flake8` configuration file
  - Used `autoflake` to remove unused imports automatically
  - Used `autopep8` to fix PEP8 style issues
  - Excluded generated gRPC files from linting
- GitHub Actions workflow improvements:
  - Added pip caching for faster CI runs
  - Updated to latest action versions (v4)
  - Added coverage artifact uploads
  - Integrated linting checks in CI pipeline

### Example Files Import Fix (older)
- Fixed import order issues in all 7 example files that were importing from `eigenda` before setting up `sys.path`
- Files fixed:
  - `blob_retrieval_example.py`
  - `check_payment_vault.py`
  - `dispersal_with_retrieval_support.py`
  - `full_example.py`
  - `minimal_client.py`
  - `test_both_payments.py`
  - `test_with_proper_payment.py`
- All examples can now be run directly with `python examples/<filename>.py` without needing PYTHONPATH
- Proper pattern: Set `sys.path` BEFORE any `eigenda` imports

### Critical Bug Fix - On-Demand Payment State Refresh (older)
- **Fixed bug in DisperserClientV2Full**: Client now refreshes payment state before each blob when using on-demand payments
- **Issue**: Client was caching cumulative payment and not syncing with server between blobs
- **Symptom**: "insufficient cumulative payment increment" errors when sending multiple blobs
- **Root cause**: `_check_payment_state()` was only called once, not refreshing for subsequent blobs
- **Fix**: Modified `_create_blob_header()` to always refresh state for on-demand payments
- **Result**: Multiple blobs can now be sent successfully without payment errors

### BlobStatus Enum Fix - V2 Protocol Alignment (older)
- **Fixed critical mismatch between Python BlobStatus enum and v2 protobuf values**
- **Issue**: Python client was using incorrect status mappings, causing status 0 (UNKNOWN) to be returned when blob was actually being processed
- **Root cause**: Python enum had different values than the actual v2 protobuf:
  - Python had: PROCESSING=1, GATHERING_SIGNATURES=2, COMPLETE=3, etc.
  - V2 protobuf has: QUEUED=1, ENCODED=2, GATHERING_SIGNATURES=3, COMPLETE=4, FAILED=5
- **Fix**: Updated BlobStatus enum and all status mappings to match v2 protobuf exactly
- **Updated files**:
  - `core/types.py`: Corrected BlobStatus enum values
  - `client_v2.py`: Fixed `_parse_blob_status()` mapping
  - `client.py`: Mock client returns QUEUED instead of PROCESSING
  - All test files updated to use new status names
- **Result**: Status values now correctly reflect actual blob processing state
- **New examples added**: `check_blob_status.py` and `check_existing_blob_status.py` for monitoring dispersal progress

### Example Files Updated (older)
- **Fixed all example files to work with the updated code**:
  - `full_example.py`: Now uses DisperserClientV2Full with correct payment_config initialization
  - `check_blob_status.py`: Fixed to pass hex string to get_blob_status() and parse response correctly
  - All examples now handle the new BlobStatus enum values (QUEUED, ENCODED, etc.)
- **Key fixes in examples**:
  - Changed `get_blob_status(blob_key)` to `get_blob_status(blob_key.hex())`
  - Parse status from response: `BlobStatus(response.status)`
  - Fixed DisperserClientV2Full initialization with PaymentConfig
  - Removed broken retrieval code from full_example.py
- **All 10 examples tested and working**:
  - Mock client examples work with new QUEUED status
  - Real dispersal examples handle payment correctly
  - Status checking examples properly monitor blob progress

### Example Files Code Quality Improvements (older)
- **Removed all sys.path hacks**: Since we're using UV, the `sys.path.insert()` hacks are no longer needed
  - Cleaned `check_blob_status.py` and `check_existing_blob_status.py`
  - All examples now import cleanly without path manipulation
- **Moved all inline imports to top of files**:
  - `full_example.py`: Moved `PaymentConfig` and `traceback` imports to top
  - `check_payment_vault.py`: Moved `traceback` import to top
  - `test_both_payments.py`: Moved `Account` import to top
  - `test_with_proper_payment.py`: Moved `traceback` import to top
- **Result**: All example files now follow Python best practices with imports at the top

### CI/CD Pipeline
The project uses GitHub Actions for comprehensive continuous integration:

**Multi-stage Pipeline**:
- **Lint Job**: Code formatting (black, isort) and linting (flake8) checks
- **Test Job**: Tests across Python 3.9-3.13 on Ubuntu, macOS, and Windows
- **Security Job**: Scans with bandit and checks dependencies with safety
- **Build Job**: Validates package building and PyPI compatibility
- **Coverage Job**: Generates reports and comments on PRs

**Local Development**:
- **Pre-commit hooks**: Automatically run black, isort, and flake8 on every commit
- **Configuration**: `.pre-commit-config.yaml` ensures consistent code quality
- **Manual checks**: `uv run pre-commit run --all-files`

## Credits

Developed and mainted by [Powerloom](https://powerloom.io/) - Original author: Swaroop Hegde (email@swaroophegde.com)
