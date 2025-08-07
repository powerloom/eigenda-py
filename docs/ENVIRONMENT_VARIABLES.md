# Environment Variables Configuration

This document describes all environment variables used by the EigenDA Python client and its examples.

## Standard Environment Variables

The following environment variables are used consistently across all examples:

### Required Variables

#### `EIGENDA_PRIVATE_KEY`
- **Description**: Your Ethereum private key (without 0x prefix)
- **Required**: Yes
- **Purpose**: Used to sign blob dispersal requests and authenticate with the disperser
- **Example**: `your_private_key_here`

### Optional Variables

#### `EIGENDA_DISPERSER_HOST`
- **Description**: Hostname of the EigenDA disperser service
- **Default**: `disperser-testnet-sepolia.eigenda.xyz`
- **Purpose**: Specifies which disperser endpoint to connect to
- **Common Values**:
  - Mainnet: `disperser.eigenda.xyz`
  - Sepolia Testnet: `disperser-testnet-sepolia.eigenda.xyz` (default)
  - Holesky Testnet: `disperser-testnet-holesky.eigenda.xyz`

#### `EIGENDA_DISPERSER_PORT`
- **Description**: Port number for the disperser service
- **Default**: `443`
- **Purpose**: Specifies the port to connect to the disperser
- **Notes**: Port 443 typically uses TLS/secure connection

#### `EIGENDA_USE_SECURE_GRPC`
- **Description**: Whether to use TLS for gRPC connections
- **Default**: `true`
- **Purpose**: Controls whether to use secure (TLS) or insecure gRPC connections
- **Values**: `true` or `false` (case-insensitive)
- **Notes**: Automatically set to `true` when port is 443

### Additional Variables (Special Cases)

#### `EIGENDA_PRIVATE_KEY_2`
- **Description**: Alternative private key for testing multiple accounts
- **Required**: No
- **Purpose**: Used in `test_both_payments.py` for testing with different accounts
- **Example**: Only needed when testing payment switching between accounts

## Usage Examples

### Basic Setup (.env file)
```bash
# Required
EIGENDA_PRIVATE_KEY=your_private_key_here

# Optional (these are the defaults)
EIGENDA_DISPERSER_HOST=disperser-testnet-sepolia.eigenda.xyz
EIGENDA_DISPERSER_PORT=443
EIGENDA_USE_SECURE_GRPC=true
```

### Mainnet Configuration
```bash
EIGENDA_PRIVATE_KEY=your_private_key_here
EIGENDA_DISPERSER_HOST=disperser.eigenda.xyz
EIGENDA_DISPERSER_PORT=443
EIGENDA_USE_SECURE_GRPC=true
```

### Holesky Testnet Configuration
```bash
EIGENDA_PRIVATE_KEY=your_private_key_here
EIGENDA_DISPERSER_HOST=disperser-testnet-holesky.eigenda.xyz
EIGENDA_DISPERSER_PORT=443
EIGENDA_USE_SECURE_GRPC=true
```

### Local Development (Insecure)
```bash
EIGENDA_PRIVATE_KEY=your_private_key_here
EIGENDA_DISPERSER_HOST=localhost
EIGENDA_DISPERSER_PORT=50051
EIGENDA_USE_SECURE_GRPC=false
```

## Loading Environment Variables

All example scripts use `python-dotenv` to automatically load variables from a `.env` file:

```python
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Access variables
private_key = os.getenv("EIGENDA_PRIVATE_KEY")
hostname = os.getenv("EIGENDA_DISPERSER_HOST", "disperser-testnet-sepolia.eigenda.xyz")
port = int(os.getenv("EIGENDA_DISPERSER_PORT", "443"))
use_secure = os.getenv("EIGENDA_USE_SECURE_GRPC", "true").lower() == "true"
```

## Files Using Environment Variables

All example files have been standardized to use these environment variables consistently:

1. **blob_retrieval_example.py** - EIGENDA_PRIVATE_KEY only
2. **check_blob_status.py** - All standard variables
3. **check_existing_blob_status.py** - All standard variables
4. **check_payment_vault.py** - EIGENDA_PRIVATE_KEY only (supports --address flag)
5. **debug_payment_state.py** - All standard variables
6. **dispersal_with_retrieval_support.py** - EIGENDA_PRIVATE_KEY only
7. **full_example.py** - EIGENDA_PRIVATE_KEY only
8. **minimal_client.py** - EIGENDA_PRIVATE_KEY only
9. **test_both_payments.py** - EIGENDA_PRIVATE_KEY and EIGENDA_PRIVATE_KEY_2
10. **test_reservation_account.py** - EIGENDA_PRIVATE_KEY only
11. **test_with_proper_payment.py** - EIGENDA_PRIVATE_KEY only

## Best Practices

1. **Never commit private keys**: Always use environment variables or `.env` files (which should be in `.gitignore`)
2. **Use defaults wisely**: The defaults point to Sepolia testnet, which is suitable for testing
3. **Consistent naming**: All EigenDA-related variables should start with `EIGENDA_` prefix
4. **Type conversion**: Remember to convert port to integer and use `.lower()` for boolean checks
5. **Error handling**: Always check if required variables (like private key) are present before using them

## Security Notes

- The `.env` file should be listed in `.gitignore` to prevent accidental commits
- Use `.env.example` to provide a template without sensitive data
- In production, use secure secret management solutions instead of `.env` files
- Never log or print private keys in your code