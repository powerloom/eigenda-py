# EigenDA Python Client - Development Notes

This document contains important implementation details and context for the EigenDA Python client.

## Project Overview

The Python client is being developed to provide Python support for EigenDA v2, with reference implementations in Go (`eigenda-client-go/`) and Rust (`eigenda-client-rs/`).

## Project Structure

The Python client is located at `/python-client/` within the eigenda-py repository and includes:

- `src/eigenda/` - Main package with client implementation
  - `client.py` - Mock client for basic testing (working)
  - `client_v2.py` - Full gRPC v2 client (authentication issues)
  - `auth/signer.py` - ECDSA signing implementation
  - `codec/blob_codec.py` - Data encoding/decoding
  - `core/types.py` - Core type definitions
  - `utils/serialization.py` - Blob key calculation (needs work)
- `src/eigenda/grpc/` - Generated gRPC stubs from proto files
- `examples/` - Example scripts demonstrating usage
  - `minimal_client.py` - Works with mock client
  - `test_v2_client.py` - Tests real gRPC (auth fails)
  - `full_example.py` - Complete dispersal/retrieval example
- `tests/` - Test suite with good coverage
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

Key dependencies:
- `grpcio` and `grpcio-tools` for gRPC
- `web3` and `eth-account` for Ethereum functionality  
- `protobuf` for message serialization
- Python 3.9+ required

### 10. Environment Setup

Using pyenv:
```bash
cd /Users/swaroop/code/eigenda-py/python-client
pyenv local 3.12.10
pip install -r requirements.txt
```

Note: The .env file defaults to Holesky testnet. To use Sepolia, uncomment the EIGENDA_DISPERSER_HOST line.

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

### Integration Tests Added (Latest)
- Added 33 comprehensive integration tests with mock gRPC servers
- Tests cover full dispersal flow, payment handling, error scenarios, and performance
- All tests pass without requiring network connections
- Fixed minor compatibility issues in examples (minimal_client.py import)

### Mock Client Tests Added
- Added 17 comprehensive tests for the mock DisperserClient
- Achieved 100% code coverage for the mock client
- Tests cover all functionality including connection management, blob dispersal, and edge cases
- Overall test coverage improved from 85% to 88%

### Test Coverage Milestone - 95% Overall Coverage! (Latest)
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

### Code Quality Improvements - 100% Linting Compliance! (Latest)
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

### Example Files Import Fix (Latest)
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

### Critical Bug Fix - On-Demand Payment State Refresh (Latest)
- **Fixed bug in DisperserClientV2Full**: Client now refreshes payment state before each blob when using on-demand payments
- **Issue**: Client was caching cumulative payment and not syncing with server between blobs
- **Symptom**: "insufficient cumulative payment increment" errors when sending multiple blobs
- **Root cause**: `_check_payment_state()` was only called once, not refreshing for subsequent blobs
- **Fix**: Modified `_create_blob_header()` to always refresh state for on-demand payments
- **Result**: Multiple blobs can now be sent successfully without payment errors

### CI/CD Pipeline
The project uses GitHub Actions for continuous integration:
- Runs tests on Python 3.9, 3.10, 3.11, and 3.12
- Lints code with flake8
- Generates coverage reports
- Caches pip dependencies for faster builds
- Uploads coverage artifacts

## Credits

Developed by [Powerloom](https://powerloom.io/) - Author: Swaroop Hegde (swaroop@powerloom.io)