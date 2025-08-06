"""Configuration utilities for EigenDA client."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class NetworkConfig:
    """Network configuration for EigenDA."""

    disperser_host: str
    disperser_port: int
    explorer_base_url: str
    network_name: str
    payment_vault_address: Optional[str] = None
    price_per_symbol: Optional[int] = None
    min_num_symbols: Optional[int] = None


# Known network configurations
NETWORK_CONFIGS = {
    "holesky": NetworkConfig(
        disperser_host="disperser-testnet-holesky.eigenda.xyz",
        disperser_port=443,
        explorer_base_url="https://blobs-v2-testnet-holesky.eigenda.xyz/blobs",
        network_name="Holesky Testnet",
        payment_vault_address="0x4a7Fff191BCDa5806f1Bc8689afc1417c08C61AB",
        price_per_symbol=447000000,  # wei per symbol
        min_num_symbols=4096,
    ),
    "sepolia": NetworkConfig(
        disperser_host="disperser-testnet-sepolia.eigenda.xyz",
        disperser_port=443,
        explorer_base_url="https://blobs-v2-testnet-sepolia.eigenda.xyz/blobs",
        network_name="Sepolia Testnet",
        payment_vault_address="0x2E1BDB221E7D6bD9B7b2365208d41A5FD70b24Ed",
        price_per_symbol=447000000,  # wei per symbol
        min_num_symbols=4096,
    ),
    "mainnet": NetworkConfig(
        disperser_host="disperser.eigenda.xyz",
        disperser_port=443,
        explorer_base_url="https://blobs.eigenda.xyz/blobs",
        network_name="Ethereum Mainnet",
        payment_vault_address="0xb2e7ef419a2A399472ae22ef5cFcCb8bE97A4B05",
        price_per_symbol=447000000,  # wei per symbol
        min_num_symbols=4096,
    ),
}


def get_network_config() -> NetworkConfig:
    """
    Get network configuration from environment or defaults.

    Checks EIGENDA_DISPERSER_HOST to determine the network.
    Falls back to Sepolia testnet if not specified.
    """
    disperser_host_env = os.environ.get("EIGENDA_DISPERSER_HOST", "")
    disperser_host = disperser_host_env.lower()

    # Determine network from disperser host
    if "sepolia" in disperser_host:
        base_config = NETWORK_CONFIGS["sepolia"]
    elif "holesky" in disperser_host:
        base_config = NETWORK_CONFIGS["holesky"]
    elif "disperser.eigenda.xyz" == disperser_host:
        base_config = NETWORK_CONFIGS["mainnet"]
    else:
        # Default to Sepolia if not recognized
        base_config = NETWORK_CONFIGS["sepolia"]

    # Create a new config with overrides
    config = NetworkConfig(
        disperser_host=os.environ.get("EIGENDA_DISPERSER_HOST", base_config.disperser_host),
        disperser_port=int(os.environ.get("EIGENDA_DISPERSER_PORT", base_config.disperser_port)),
        explorer_base_url=base_config.explorer_base_url,
        network_name=base_config.network_name,
        payment_vault_address=base_config.payment_vault_address,
        price_per_symbol=base_config.price_per_symbol,
        min_num_symbols=base_config.min_num_symbols,
    )

    return config


def get_disperser_endpoint() -> tuple[str, int]:
    """Get disperser endpoint from environment or defaults."""
    config = get_network_config()
    return config.disperser_host, config.disperser_port


def get_explorer_url(blob_key: str) -> str:
    """Get explorer URL for a blob key based on current network."""
    config = get_network_config()
    return f"{config.explorer_base_url}/{blob_key}"
