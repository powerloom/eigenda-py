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

As of the last session:
- ✅ Basic client structure implemented
- ✅ gRPC communication working
- ✅ Data encoding/decoding implemented
- ✅ Mock DisperserClient for testing
- ✅ Full DisperserClientV2 with gRPC
- ⚠️ Signature verification issues with disperser (recovery ID problem)
- ⚠️ Payment state authentication not fully working

### 6. Testing

To test the client:
1. Set `EIGENDA_PRIVATE_KEY` environment variable
2. Run `python examples/minimal_client.py` (uses mock client)
3. Run `python examples/test_v2_client.py` (uses real gRPC)

### 7. Known Issues and Progress

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

### 8. Dependencies

Key dependencies:
- `grpcio` and `grpcio-tools` for gRPC
- `web3` and `eth-account` for Ethereum functionality  
- `protobuf` for message serialization
- Python 3.8+ required

### 9. Environment Setup

Using pyenv:
```bash
cd /Users/swaroop/code/eigenda-py/python-client
pyenv local 3.12.10
pip install -r requirements.txt
```

Note: The .env file defaults to Holesky testnet. To use Sepolia, uncomment the EIGENDA_DISPERSER_HOST line.

## Next Steps

1. ✅ ~~Fix signature recovery issue~~ - DONE
2. ✅ ~~Implement proper blob key calculation~~ - DONE
3. ✅ ~~Implement on-demand payment support~~ - DONE
4. Add comprehensive integration tests
5. ✅ ~~Create a clean client API that handles both reservation and on-demand payments~~ - DONE (DisperserClientV2Full)
6. ⚠️ Add support for blob retrieval from relays - Basic implementation exists but needs relay endpoints
7. Implement local KZG commitment calculation (optional)

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

## Working Example

Successfully dispersed blobs on both testnets:
- Holesky Blob: `3aaf8a5f848e53a5ecaff30de372a5c0931468d0f46b64fcc5d3984692c0f109`
- Sepolia Blob: `95ae8a8aa08fec0354f439eef31b351da97972916f0bb1c8b4ff8e50a82dc080`

Key discoveries:
- Must use SHA256(Keccak256(...)) for payment state authentication
- On-demand payment requires calculating cost based on blob size (min 4096 symbols)
- Price per symbol on Holesky: 447000000 wei
- Account has 1 ETH deposited in PaymentVault contract on Holesky