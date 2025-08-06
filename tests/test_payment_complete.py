"""Complete tests for payment.py to achieve 100% coverage."""

import pytest

from eigenda.payment import (
    PaymentConfig,
    SimpleAccountant,
    calculate_payment_increment,
    get_blob_length_power_of_2,
)


class TestPaymentConfig:
    """Complete tests for PaymentConfig class."""

    def test_payment_config_defaults(self):
        """Test default values."""
        config = PaymentConfig()
        assert config.price_per_symbol == 447000000
        assert config.min_num_symbols == 4096

    def test_payment_config_custom_values(self):
        """Test custom values."""
        config = PaymentConfig(price_per_symbol=1000, min_num_symbols=2048)
        assert config.price_per_symbol == 1000
        assert config.min_num_symbols == 2048

    def test_payment_config_negative_price(self):
        """Test validation for negative price (line 16)."""
        with pytest.raises(ValueError, match="price_per_symbol cannot be negative"):
            PaymentConfig(price_per_symbol=-100)

    def test_payment_config_zero_min_symbols(self):
        """Test validation for zero min_symbols (line 18)."""
        with pytest.raises(ValueError, match="min_num_symbols must be positive"):
            PaymentConfig(min_num_symbols=0)

    def test_payment_config_negative_min_symbols(self):
        """Test validation for negative min_symbols (line 18)."""
        with pytest.raises(ValueError, match="min_num_symbols must be positive"):
            PaymentConfig(min_num_symbols=-1)


class TestGetBlobLengthPowerOf2:
    """Complete tests for get_blob_length_power_of_2 function."""

    def test_zero_length(self):
        """Test with zero length (line 35)."""
        assert get_blob_length_power_of_2(0) == 0

    def test_very_small_data(self):
        """Test with data that results in 0 symbols (line 42)."""
        # With 0 bytes after calculation, should return 1
        assert get_blob_length_power_of_2(1) == 1  # (1 + 30) // 31 = 1

    def test_zero_symbols_edge_case(self):
        """Test edge case that would result in 0 symbols but isn't 0 length."""
        # This is a theoretical test - in practice, (data_len + 30) // 31
        # will always be >= 1 if data_len > 0
        # But let's test the logic path anyway by testing the boundary
        # Actually, with the formula (data_len + 30) // 31, the minimum non-zero result is 1
        # So this test just confirms the formula works correctly
        assert get_blob_length_power_of_2(1) == 1  # Minimum case

    def test_exact_symbol_boundary(self):
        """Test data that fits exactly in symbols."""
        # 31 bytes: (31 + 30) // 31 = 61 // 31 = 1.97, so 1 symbol, already power of 2
        assert get_blob_length_power_of_2(31) == 1
        # 1 byte: (1 + 30) // 31 = 31 // 31 = 1
        assert get_blob_length_power_of_2(1) == 1
        # 32 bytes: (32 + 30) // 31 = 62 // 31 = 2
        assert get_blob_length_power_of_2(32) == 2

    def test_power_of_2_rounding(self):
        """Test power of 2 rounding."""
        # 93 bytes: (93 + 30) // 31 = 123 // 31 = 3.96, so 3 symbols, round to 4
        assert get_blob_length_power_of_2(93) == 4
        # 94 bytes: (94 + 30) // 31 = 124 // 31 = 4
        assert get_blob_length_power_of_2(94) == 4
        # 124 bytes: (124 + 30) // 31 = 154 // 31 = 4.96, so 4 symbols, already power of 2
        assert get_blob_length_power_of_2(124) == 4
        # 125 bytes: (125 + 30) // 31 = 155 // 31 = 5, round to 8
        assert get_blob_length_power_of_2(125) == 8


class TestCalculatePaymentIncrement:
    """Complete tests for calculate_payment_increment function."""

    def test_with_default_config(self):
        """Test with default config (line 67)."""
        # 100 bytes = 4 symbols, round to 4, but min is 4096
        payment = calculate_payment_increment(100)
        assert payment == 4096 * 447000000

    def test_with_custom_config(self):
        """Test with custom config."""
        config = PaymentConfig(price_per_symbol=1000, min_num_symbols=8)

        # 100 bytes = 4 symbols, round to 4, but min is 8
        payment = calculate_payment_increment(100, config)
        assert payment == 8 * 1000

    def test_below_minimum_symbols(self):
        """Test when calculated symbols are below minimum (line 74)."""
        config = PaymentConfig(price_per_symbol=100, min_num_symbols=16)

        # 31 bytes = 2 symbols, but min is 16
        payment = calculate_payment_increment(31, config)
        assert payment == 16 * 100

    def test_above_minimum_symbols(self):
        """Test when calculated symbols are above minimum."""
        config = PaymentConfig(price_per_symbol=100, min_num_symbols=4)

        # 125 bytes: (125 + 30) // 31 = 5 symbols, round to 8 (above min of 4)
        payment = calculate_payment_increment(125, config)
        assert payment == 8 * 100


class TestSimpleAccountant:
    """Complete tests for SimpleAccountant class."""

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        accountant = SimpleAccountant("0x123")
        assert accountant.account_id == "0x123"
        assert accountant.cumulative_payment == 0
        assert accountant.config.price_per_symbol == 447000000

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = PaymentConfig(price_per_symbol=1000, min_num_symbols=8)
        accountant = SimpleAccountant("0x456", config)
        assert accountant.account_id == "0x456"
        assert accountant.cumulative_payment == 0
        assert accountant.config.price_per_symbol == 1000

    def test_set_cumulative_payment(self):
        """Test set_cumulative_payment method (line 97)."""
        accountant = SimpleAccountant("0x789")
        accountant.set_cumulative_payment(1000000)
        assert accountant.cumulative_payment == 1000000

    def test_account_blob(self):
        """Test account_blob method (lines 110-120)."""
        config = PaymentConfig(price_per_symbol=100, min_num_symbols=4)
        accountant = SimpleAccountant("0xabc", config)
        accountant.set_cumulative_payment(500)

        # 100 bytes = 4 symbols (at minimum)
        payment_bytes, increment = accountant.account_blob(100)

        assert increment == 4 * 100  # 400
        assert payment_bytes == (500 + 400).to_bytes(2, "big")  # 900 fits in 2 bytes

    def test_account_blob_large_payment(self):
        """Test account_blob with large payment requiring more bytes."""
        config = PaymentConfig(price_per_symbol=10**18, min_num_symbols=10)
        accountant = SimpleAccountant("0xdef", config)

        # This will create a very large payment
        payment_bytes, increment = accountant.account_blob(1000)

        expected_increment = 64 * 10**18  # 64 symbols (power of 2 > 33)
        assert increment == expected_increment

        # Verify the bytes representation is correct
        expected_total = expected_increment
        assert int.from_bytes(payment_bytes, "big") == expected_total
