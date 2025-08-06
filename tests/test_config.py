"""Tests for network configuration."""

import os
from unittest.mock import patch

import pytest

from eigenda.config import (
    NETWORK_CONFIGS,
    NetworkConfig,
    get_disperser_endpoint,
    get_explorer_url,
    get_network_config,
)


class TestNetworkConfig:
    """Test network configuration functionality."""

    def test_network_config_creation(self):
        """Test creating network configuration."""
        config = NetworkConfig(
            disperser_host="test.eigenda.xyz",
            disperser_port=443,
            explorer_base_url="https://explorer.test",
            network_name="Test Network",
            payment_vault_address="0x1234567890123456789012345678901234567890",
            price_per_symbol=1000000,
            min_num_symbols=100,
        )

        assert config.disperser_host == "test.eigenda.xyz"
        assert config.disperser_port == 443
        assert config.explorer_base_url == "https://explorer.test"
        assert config.network_name == "Test Network"
        assert config.payment_vault_address == "0x1234567890123456789012345678901234567890"
        assert config.price_per_symbol == 1000000
        assert config.min_num_symbols == 100

    def test_predefined_networks(self):
        """Test that all predefined networks are properly configured."""
        # Check Holesky
        holesky = NETWORK_CONFIGS["holesky"]
        assert holesky.disperser_host == "disperser-testnet-holesky.eigenda.xyz"
        assert holesky.disperser_port == 443
        assert holesky.payment_vault_address == "0x4a7Fff191BCDa5806f1Bc8689afc1417c08C61AB"
        assert holesky.price_per_symbol == 447000000
        assert holesky.min_num_symbols == 4096

        # Check Sepolia
        sepolia = NETWORK_CONFIGS["sepolia"]
        assert sepolia.disperser_host == "disperser-testnet-sepolia.eigenda.xyz"
        assert sepolia.disperser_port == 443
        assert sepolia.payment_vault_address == "0x2E1BDB221E7D6bD9B7b2365208d41A5FD70b24Ed"
        assert sepolia.price_per_symbol == 447000000
        assert sepolia.min_num_symbols == 4096

        # Check Mainnet
        mainnet = NETWORK_CONFIGS["mainnet"]
        assert mainnet.disperser_host == "disperser.eigenda.xyz"
        assert mainnet.disperser_port == 443
        assert mainnet.payment_vault_address == "0xb2e7ef419a2A399472ae22ef5cFcCb8bE97A4B05"
        assert mainnet.price_per_symbol == 447000000
        assert mainnet.min_num_symbols == 4096

    @patch.dict(os.environ, {}, clear=True)
    def test_get_network_config_default(self):
        """Test getting network config with no environment variable."""
        config = get_network_config()

        # Should default to Sepolia
        assert config.network_name == "Sepolia Testnet"
        assert config.disperser_host == "disperser-testnet-sepolia.eigenda.xyz"

    @patch.dict(os.environ, {"EIGENDA_DISPERSER_HOST": "disperser-testnet-sepolia.eigenda.xyz"})
    def test_get_network_config_sepolia(self):
        """Test getting Sepolia network config from environment."""
        config = get_network_config()

        assert config.network_name == "Sepolia Testnet"
        assert config.disperser_host == "disperser-testnet-sepolia.eigenda.xyz"
        assert config.payment_vault_address == "0x2E1BDB221E7D6bD9B7b2365208d41A5FD70b24Ed"

    @patch.dict(os.environ, {"EIGENDA_DISPERSER_HOST": "disperser-testnet-holesky.eigenda.xyz"})
    def test_get_network_config_holesky(self):
        """Test getting Holesky network config from environment."""
        config = get_network_config()

        assert config.network_name == "Holesky Testnet"
        assert config.disperser_host == "disperser-testnet-holesky.eigenda.xyz"
        assert config.payment_vault_address == "0x4a7Fff191BCDa5806f1Bc8689afc1417c08C61AB"

    @patch.dict(os.environ, {"EIGENDA_DISPERSER_HOST": "disperser.eigenda.xyz"})
    def test_get_network_config_mainnet(self):
        """Test getting mainnet config from environment."""
        config = get_network_config()

        assert config.network_name == "Ethereum Mainnet"
        assert config.disperser_host == "disperser.eigenda.xyz"
        assert config.payment_vault_address == "0xb2e7ef419a2A399472ae22ef5cFcCb8bE97A4B05"

    @patch.dict(os.environ, {"EIGENDA_DISPERSER_HOST": "custom.eigenda.xyz"})
    def test_get_network_config_custom(self):
        """Test getting config with custom host."""
        config = get_network_config()

        # Should use Sepolia as base but with custom host
        assert config.network_name == "Sepolia Testnet"  # Defaults to Sepolia
        assert config.disperser_host == "custom.eigenda.xyz"  # But uses custom host
        assert config.payment_vault_address == "0x2E1BDB221E7D6bD9B7b2365208d41A5FD70b24Ed"

    @patch.dict(
        os.environ,
        {
            "EIGENDA_DISPERSER_HOST": "disperser-testnet-sepolia.eigenda.xyz",
            "EIGENDA_DISPERSER_PORT": "8443",
        },
    )
    def test_get_network_config_with_port(self):
        """Test getting config with custom port."""
        config = get_network_config()

        assert config.network_name == "Sepolia Testnet"
        assert config.disperser_host == "disperser-testnet-sepolia.eigenda.xyz"
        assert config.disperser_port == 8443  # Custom port

    @patch.dict(os.environ, {"EIGENDA_DISPERSER_HOST": "DISPERSER-TESTNET-SEPOLIA.EIGENDA.XYZ"})
    def test_get_network_config_case_insensitive(self):
        """Test that network detection is case insensitive."""
        config = get_network_config()

        assert config.network_name == "Sepolia Testnet"
        assert config.disperser_host == "DISPERSER-TESTNET-SEPOLIA.EIGENDA.XYZ"  # Preserves case

    def test_get_disperser_endpoint(self):
        """Test getting disperser endpoint."""
        with patch.dict(os.environ, {"EIGENDA_DISPERSER_HOST": "test.eigenda.xyz"}):
            host, port = get_disperser_endpoint()
            assert host == "test.eigenda.xyz"
            assert port == 443

        with patch.dict(
            os.environ,
            {"EIGENDA_DISPERSER_HOST": "test.eigenda.xyz", "EIGENDA_DISPERSER_PORT": "8080"},
        ):
            host, port = get_disperser_endpoint()
            assert host == "test.eigenda.xyz"
            assert port == 8080

    def test_get_explorer_url(self):
        """Test getting explorer URL for blob."""
        blob_key = "a" * 64

        # Test with Sepolia (default)
        with patch.dict(os.environ, {}, clear=True):
            url = get_explorer_url(blob_key)
            assert url == f"https://blobs-v2-testnet-sepolia.eigenda.xyz/blobs/{blob_key}"

        # Test with Holesky
        with patch.dict(
            os.environ, {"EIGENDA_DISPERSER_HOST": "disperser-testnet-holesky.eigenda.xyz"}
        ):
            url = get_explorer_url(blob_key)
            assert url == f"https://blobs-v2-testnet-holesky.eigenda.xyz/blobs/{blob_key}"

        # Test with mainnet
        with patch.dict(os.environ, {"EIGENDA_DISPERSER_HOST": "disperser.eigenda.xyz"}):
            url = get_explorer_url(blob_key)
            assert url == f"https://blobs.eigenda.xyz/blobs/{blob_key}"

    def test_network_config_immutability(self):
        """Test that network configs are not accidentally modified."""
        # Get a config
        config = get_network_config()
        original_host = config.disperser_host

        # Try to modify it (this shouldn't affect future calls)
        config.disperser_host = "modified.host"

        # Get config again
        new_config = get_network_config()

        # Should not be modified
        assert new_config.disperser_host == original_host

    @patch.dict(os.environ, {"EIGENDA_DISPERSER_PORT": "not_a_number"})
    def test_invalid_port_configuration(self):
        """Test handling of invalid port configuration."""
        with pytest.raises(ValueError):
            get_network_config()
