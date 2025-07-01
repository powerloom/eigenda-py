"""Tests for payment-related functionality - fixed version."""

import pytest
from eigenda.payment import (
    PaymentConfig, 
    calculate_payment_increment,
    get_blob_length_power_of_2,
    SimpleAccountant
)


class TestPaymentCalculation:
    """Test payment calculation utilities."""
    
    def test_payment_config_creation(self):
        """Test creating payment configuration."""
        config = PaymentConfig(
            price_per_symbol=447000000,
            min_num_symbols=4096
        )
        
        assert config.price_per_symbol == 447000000
        assert config.min_num_symbols == 4096
    
    def test_calculate_payment_increment_minimum(self):
        """Test payment calculation for minimum size."""
        config = PaymentConfig(
            price_per_symbol=447000000,
            min_num_symbols=4096
        )
        
        # Data smaller than minimum should still pay for minimum
        small_data_len = 100  # Less than 4096 symbols
        payment = calculate_payment_increment(small_data_len, config)
        
        # 100 bytes = 4 symbols (power of 2), but min is 4096
        expected = 447000000 * 4096
        assert payment == expected
    
    def test_calculate_payment_increment_exact_4096_symbols(self):
        """Test payment calculation for exactly 4096 symbols worth of data."""
        config = PaymentConfig(
            price_per_symbol=447000000,
            min_num_symbols=4096
        )
        
        # 31 * 4096 = 126976 bytes = exactly 4096 symbols
        data_len = 31 * 4096
        payment = calculate_payment_increment(data_len, config)
        
        expected = 447000000 * 4096
        assert payment == expected
    
    def test_calculate_payment_increment_above_minimum(self):
        """Test payment calculation for data above minimum."""
        config = PaymentConfig(
            price_per_symbol=447000000,
            min_num_symbols=4096
        )
        
        # 31 * 8192 = 253952 bytes = 8192 symbols
        data_len = 31 * 8192
        payment = calculate_payment_increment(data_len, config)
        
        expected = 447000000 * 8192
        assert payment == expected
    
    def test_calculate_payment_increment_partial_symbol(self):
        """Test payment calculation with partial symbol."""
        config = PaymentConfig(
            price_per_symbol=447000000,
            min_num_symbols=4096
        )
        
        # 31 * 4096 + 1 = 126977 bytes = 4097 symbols, rounds to 8192
        data_len = 31 * 4096 + 1
        payment = calculate_payment_increment(data_len, config)
        
        expected = 447000000 * 8192  # Rounds up to next power of 2
        assert payment == expected
    
    def test_calculate_payment_zero_data(self):
        """Test payment calculation for zero data."""
        config = PaymentConfig(
            price_per_symbol=447000000,
            min_num_symbols=4096
        )
        
        payment = calculate_payment_increment(0, config)
        
        # Even zero data pays for minimum
        expected = 447000000 * 4096
        assert payment == expected
    
    def test_calculate_payment_large_data(self):
        """Test payment calculation for large data."""
        config = PaymentConfig(
            price_per_symbol=447000000,
            min_num_symbols=4096
        )
        
        # 1MB of data
        data_len = 1024 * 1024
        # (1048576 + 30) // 31 = 33825 symbols
        # Next power of 2 is 65536
        payment = calculate_payment_increment(data_len, config)
        
        expected = 447000000 * 65536
        assert payment == expected
    
    def test_payment_config_with_different_prices(self):
        """Test payment calculation with different price configurations."""
        # Test with a different price
        config = PaymentConfig(
            price_per_symbol=1000000000,  # 1 gwei per symbol
            min_num_symbols=1000
        )
        
        # 31 * 2000 = 62000 bytes = 2000 symbols, rounds to 2048
        data_len = 31 * 2000
        payment = calculate_payment_increment(data_len, config)
        
        expected = 1000000000 * 2048
        assert payment == expected
    
    def test_payment_edge_cases(self):
        """Test edge cases in payment calculation."""
        config = PaymentConfig(
            price_per_symbol=1,  # Minimum price
            min_num_symbols=1    # Minimum symbols
        )
        
        # Test with 1 byte (should be 1 symbol)
        payment = calculate_payment_increment(1, config)
        assert payment == 1
        
        # Test with 31 bytes (exactly 1 symbol)
        payment = calculate_payment_increment(31, config)
        assert payment == 1
        
        # Test with 32 bytes (2 symbols)
        payment = calculate_payment_increment(32, config)
        assert payment == 2
    
    def test_payment_config_validation(self):
        """Test payment config validation."""
        # Negative price should raise error
        with pytest.raises(ValueError):
            PaymentConfig(
                price_per_symbol=-1,
                min_num_symbols=4096
            )
        
        # Zero price should be allowed (free tier)
        config = PaymentConfig(
            price_per_symbol=0,
            min_num_symbols=4096
        )
        assert config.price_per_symbol == 0
        
        # Negative min symbols should raise error
        with pytest.raises(ValueError):
            PaymentConfig(
                price_per_symbol=447000000,
                min_num_symbols=-1
            )
        
        # Zero min symbols should raise error
        with pytest.raises(ValueError):
            PaymentConfig(
                price_per_symbol=447000000,
                min_num_symbols=0
            )


class TestBlobLengthCalculation:
    """Test blob length power of 2 calculation."""
    
    def test_get_blob_length_zero(self):
        """Test blob length calculation for zero data."""
        assert get_blob_length_power_of_2(0) == 0
    
    def test_get_blob_length_small(self):
        """Test blob length calculation for small data."""
        # 1-31 bytes = 1 symbol = 1 (power of 2)
        assert get_blob_length_power_of_2(1) == 1
        assert get_blob_length_power_of_2(30) == 1
        assert get_blob_length_power_of_2(31) == 1
        
        # 32 bytes = 2 symbols = 2 (power of 2)
        assert get_blob_length_power_of_2(32) == 2
    
    def test_get_blob_length_powers_of_2(self):
        """Test blob length calculation for exact powers of 2."""
        # 31 bytes = 1 symbol = 1
        assert get_blob_length_power_of_2(31) == 1
        
        # 62 bytes = 2 symbols = 2
        assert get_blob_length_power_of_2(62) == 2
        
        # 124 bytes = 4 symbols = 4
        assert get_blob_length_power_of_2(124) == 4
        
        # 248 bytes = 8 symbols = 8
        assert get_blob_length_power_of_2(248) == 8
    
    def test_get_blob_length_round_up(self):
        """Test blob length calculation rounds up to power of 2."""
        # 63 bytes = 3 symbols = 4 (round up)
        assert get_blob_length_power_of_2(63) == 4
        
        # 125 bytes = 5 symbols = 8 (round up)
        assert get_blob_length_power_of_2(125) == 8
        
        # 249 bytes = 9 symbols = 16 (round up)
        assert get_blob_length_power_of_2(249) == 16
    
    def test_get_blob_length_large(self):
        """Test blob length calculation for large data."""
        # 31 * 4096 = 126976 bytes = 4096 symbols
        assert get_blob_length_power_of_2(31 * 4096) == 4096
        
        # One more byte should round up to 8192
        assert get_blob_length_power_of_2(31 * 4096 + 1) == 8192
        
        # 1MB of data
        mb_data = 1024 * 1024
        # Should round up to 65536
        assert get_blob_length_power_of_2(mb_data) == 65536


class TestSimpleAccountant:
    """Test SimpleAccountant for payment tracking."""
    
    def test_accountant_creation(self):
        """Test creating accountant."""
        accountant = SimpleAccountant("0x1234567890123456789012345678901234567890")
        
        assert accountant.account_id == "0x1234567890123456789012345678901234567890"
        assert accountant.cumulative_payment == 0
        assert accountant.config.price_per_symbol == 447000000
        assert accountant.config.min_num_symbols == 4096
    
    def test_accountant_with_custom_config(self):
        """Test creating accountant with custom config."""
        config = PaymentConfig(price_per_symbol=1000000000, min_num_symbols=1000)
        accountant = SimpleAccountant(
            "0x1234567890123456789012345678901234567890",
            config
        )
        
        assert accountant.config.price_per_symbol == 1000000000
        assert accountant.config.min_num_symbols == 1000
    
    def test_set_cumulative_payment(self):
        """Test setting cumulative payment."""
        accountant = SimpleAccountant("0x1234567890123456789012345678901234567890")
        
        accountant.set_cumulative_payment(1000000000000)
        assert accountant.cumulative_payment == 1000000000000
    
    def test_account_blob_first_payment(self):
        """Test accounting for first blob."""
        accountant = SimpleAccountant("0x1234567890123456789012345678901234567890")
        
        # Account for minimum size blob
        # 31 * 4096 = exactly 4096 symbols
        data_len = 31 * 4096
        payment_bytes, increment = accountant.account_blob(data_len)
        
        expected_increment = 447000000 * 4096
        assert increment == expected_increment
        
        # Check payment bytes
        assert int.from_bytes(payment_bytes, 'big') == expected_increment
    
    def test_account_blob_cumulative(self):
        """Test accounting for multiple blobs."""
        accountant = SimpleAccountant("0x1234567890123456789012345678901234567890")
        
        # First blob (4096 symbols)
        data_len = 31 * 4096
        payment_bytes1, increment1 = accountant.account_blob(data_len)
        
        # Update cumulative payment
        accountant.set_cumulative_payment(int.from_bytes(payment_bytes1, 'big'))
        
        # Second blob (8192 symbols)
        data_len2 = 31 * 8192
        payment_bytes2, increment2 = accountant.account_blob(data_len2)
        
        # Check increments
        assert increment1 == 447000000 * 4096
        assert increment2 == 447000000 * 8192
        
        # Check cumulative payment
        total = int.from_bytes(payment_bytes2, 'big')
        assert total == increment1 + increment2
    
    def test_account_blob_payment_bytes_format(self):
        """Test payment bytes format."""
        accountant = SimpleAccountant("0x1234567890123456789012345678901234567890")
        
        # Small payment (1 byte = 1 symbol, but min is 4096)
        data_len = 1
        payment_bytes, _ = accountant.account_blob(data_len)
        
        # Should be big-endian bytes
        payment_int = int.from_bytes(payment_bytes, 'big')
        assert payment_int == 447000000 * 4096
        
        # Large existing payment
        accountant.set_cumulative_payment(10**18)  # 1 ETH
        payment_bytes2, _ = accountant.account_blob(data_len)
        
        payment_int2 = int.from_bytes(payment_bytes2, 'big')
        assert payment_int2 == 10**18 + 447000000 * 4096
    
    def test_account_blob_zero_price(self):
        """Test accounting with zero price (free tier)."""
        config = PaymentConfig(price_per_symbol=0, min_num_symbols=4096)
        accountant = SimpleAccountant(
            "0x1234567890123456789012345678901234567890",
            config
        )
        
        data_len = 31 * 8192
        payment_bytes, increment = accountant.account_blob(data_len)
        
        assert increment == 0
        assert int.from_bytes(payment_bytes, 'big') == 0