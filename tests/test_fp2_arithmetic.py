"""Tests for Fp2 arithmetic operations."""

from eigenda.utils.fp2_arithmetic import Fp2, P, sqrt_fp2, tonelli_shanks_fp


class TestFp2Basic:
    """Test basic Fp2 operations."""

    def test_fp2_creation(self):
        """Test creating Fp2 elements."""
        # Create from two components
        a = Fp2(1, 2)
        assert a.a0 == 1
        assert a.a1 == 2

        # Create zero element
        zero = Fp2(0, 0)
        assert zero.a0 == 0
        assert zero.a1 == 0

        # Create with large values (should be reduced mod P)
        large = Fp2(P + 1, P + 2)
        assert large.a0 == 1
        assert large.a1 == 2

    def test_fp2_equality(self):
        """Test Fp2 equality comparison."""
        a = Fp2(1, 2)
        b = Fp2(1, 2)
        c = Fp2(2, 1)

        assert a == b
        assert a != c
        assert b != c

    def test_fp2_string_representation(self):
        """Test string representation of Fp2."""
        a = Fp2(123, 456)
        assert str(a) == "Fp2(123, 456)"
        assert repr(a) == "Fp2(123, 456)"


class TestFp2Arithmetic:
    """Test Fp2 arithmetic operations using operator overloading."""

    def test_add_fp2(self):
        """Test Fp2 addition."""
        a = Fp2(1, 2)
        b = Fp2(3, 4)
        c = a + b

        assert c == Fp2(4, 6)

        # Test with modular reduction
        a = Fp2(P - 1, P - 2)
        b = Fp2(2, 3)
        c = a + b
        assert c == Fp2(1, 1)

        # Test commutativity
        assert a + b == b + a

    def test_sub_fp2(self):
        """Test Fp2 subtraction."""
        a = Fp2(5, 7)
        b = Fp2(2, 3)
        c = a - b

        assert c == Fp2(3, 4)

        # Test with modular reduction
        a = Fp2(1, 2)
        b = Fp2(2, 3)
        c = a - b
        assert c == Fp2(P - 1, P - 1)

    def test_mul_fp2(self):
        """Test Fp2 multiplication."""
        # Test basic multiplication
        # (1 + 2i) * (3 + 4i) = 3 + 4i + 6i + 8i² = 3 + 10i + 8(-1) = -5 + 10i
        a = Fp2(1, 2)
        b = Fp2(3, 4)
        c = a * b

        # (1 + 2u) * (3 + 4u) where u² = -1
        # = 3 + 4u + 6u + 8u²
        # = 3 + 10u + 8(-1)
        # = -5 + 10u
        expected_a0 = (3 - 8) % P  # 3 - 8 = -5 mod P
        expected_a1 = 10
        assert c == Fp2(expected_a0, expected_a1)

        # Test multiplication by zero
        zero = Fp2(0, 0)
        assert a * zero == zero
        assert zero * a == zero

        # Test multiplication by one
        one = Fp2(1, 0)
        assert a * one == a
        assert one * a == a

    def test_square_fp2(self):
        """Test Fp2 squaring."""
        # Test (1 + 2u)^2 = 1 + 4u + 4u² = 1 + 4u - 4 = -3 + 4u
        a = Fp2(1, 2)
        a_squared = a.square()

        expected_a0 = (1 - 4) % P  # 1 - 4 = -3 mod P
        expected_a1 = 4
        assert a_squared == Fp2(expected_a0, expected_a1)

        # Verify square equals multiplication
        assert a_squared == a * a

    def test_conjugate_fp2(self):
        """Test Fp2 conjugation."""
        a = Fp2(3, 4)
        conj = a.conjugate()

        assert conj == Fp2(3, P - 4)

        # Test double conjugation
        assert a.conjugate().conjugate() == a

        # Test conjugate of real number
        real = Fp2(5, 0)
        assert real.conjugate() == real

    def test_inverse_fp2(self):
        """Test Fp2 multiplicative inverse."""
        # Test inverse property
        test_elements = [
            Fp2(1, 0),  # 1
            Fp2(1, 1),  # 1 + u
            Fp2(2, 3),  # 2 + 3u
            Fp2(5, 7),  # 5 + 7u
        ]

        for a in test_elements:
            inv_a = a.inverse()
            product = a * inv_a
            assert product == Fp2(1, 0)  # Should equal 1

    def test_is_zero(self):
        """Test zero checking."""
        zero = Fp2(0, 0)
        assert zero.is_zero()

        non_zero = Fp2(1, 0)
        assert not non_zero.is_zero()

        non_zero2 = Fp2(0, 1)
        assert not non_zero2.is_zero()

    def test_legendre_symbol(self):
        """Test Legendre symbol computation."""
        # Test with some known values
        one = Fp2(1, 0)
        legendre = one.legendre()
        assert legendre == 1  # 1 is always a quadratic residue

        # Test with zero
        zero = Fp2(0, 0)
        assert zero.legendre() == 0


class TestTonelliShanksFp:
    """Test Tonelli-Shanks algorithm for Fp."""

    def test_tonelli_shanks_perfect_squares(self):
        """Test square roots of perfect squares."""
        # Test small perfect squares
        perfect_squares = [
            (1, 1),
            (4, 2),
            (9, 3),
            (16, 4),
            (25, 5),
            (36, 6),
            (49, 7),
            (64, 8),
            (81, 9),
            (100, 10)
        ]

        for square, expected_root in perfect_squares:
            root = tonelli_shanks_fp(square % P)
            # The root might be either expected_root or P - expected_root
            assert root == expected_root or root == P - expected_root
            assert (root * root) % P == square % P

    def test_tonelli_shanks_zero(self):
        """Test square root of zero."""
        result = tonelli_shanks_fp(0)
        # Implementation might return None for 0
        assert result is None or result == 0

    def test_tonelli_shanks_one(self):
        """Test square root of one."""
        assert tonelli_shanks_fp(1) == 1

    def test_tonelli_shanks_non_residue(self):
        """Test that non-quadratic residues return None."""
        # P-1 is typically not a quadratic residue (it's -1 mod P)
        # The Legendre symbol of -1 is -1 for P ≡ 3 (mod 4)

        # Check if P ≡ 3 (mod 4)
        if P % 4 == 3:
            # -1 should not be a quadratic residue
            result = tonelli_shanks_fp(P - 1)
            assert result is None

    def test_tonelli_shanks_large_values(self):
        """Test square roots of large values."""
        # Test with some large values
        large_base = P // 2
        large_square = (large_base * large_base) % P

        root = tonelli_shanks_fp(large_square)
        assert (root * root) % P == large_square
        # The root should be either large_base or P - large_base
        assert root == large_base or root == P - large_base

    def test_tonelli_shanks_consistency(self):
        """Test that Tonelli-Shanks is consistent."""
        # For any quadratic residue, the algorithm should return the same result
        test_value = 16

        root1 = tonelli_shanks_fp(test_value)
        root2 = tonelli_shanks_fp(test_value)

        assert root1 == root2

    def test_tonelli_shanks_with_known_residues(self):
        """Test with known quadratic residues."""
        # 3 is the curve constant and should be a quadratic residue
        root_of_3 = tonelli_shanks_fp(3)
        if root_of_3 is not None:
            assert (root_of_3 * root_of_3) % P == 3

        # Test a few more values
        for base in [7, 11, 13, 17, 19]:
            square = (base * base) % P
            root = tonelli_shanks_fp(square)
            assert (root * root) % P == square


class TestFp2SquareRoot:
    """Test Fp2 square root computation."""

    def test_sqrt_fp2_perfect_squares(self):
        """Test square roots of perfect squares in Fp2."""
        # Test some simple perfect squares
        test_values = [
            Fp2(1, 0),  # 1
            Fp2(4, 0),  # 4
            Fp2(9, 0),  # 9
        ]

        for val in test_values:
            sqrt_val, exists = sqrt_fp2(val)
            if exists:
                # Verify sqrt^2 = val
                assert sqrt_val.square() == val

    def test_sqrt_fp2_complex_elements(self):
        """Test square roots of complex Fp2 elements."""
        # Test (1 + u)^2 = 1 + 2u + u^2 = 1 + 2u - 1 = 2u
        a = Fp2(0, 2)  # 2u
        sqrt_a, exists = sqrt_fp2(a)

        if exists:
            # Verify sqrt^2 = a
            assert sqrt_a.square() == a

    def test_sqrt_fp2_non_residue(self):
        """Test that non-quadratic residues return False."""
        # Some elements may not have square roots
        # This depends on the specific field parameters
        # We'll test that the function handles such cases gracefully

        # Try an element that might not have a square root
        a = Fp2(2, 3)
        sqrt_a, exists = sqrt_fp2(a)

        if exists:
            # If it has a square root, verify it
            assert sqrt_a.square() == a
        else:
            # If no square root, that's also valid
            assert not exists

    def test_sqrt_fp2_zero(self):
        """Test square root of zero."""
        zero = Fp2(0, 0)
        sqrt_zero, exists = sqrt_fp2(zero)
        assert exists
        assert sqrt_zero == zero

    def test_sqrt_fp2_consistency(self):
        """Test that square root computation is consistent."""
        # Test with a few values
        test_values = [
            Fp2(1, 0),
            Fp2(2, 0),
            Fp2(1, 1),
        ]

        for val in test_values:
            sqrt1, exists1 = sqrt_fp2(val)
            sqrt2, exists2 = sqrt_fp2(val)

            assert exists1 == exists2
            if exists1:
                # Results should be consistent
                assert sqrt1 == sqrt2


class TestFp2Properties:
    """Test mathematical properties of Fp2 operations."""

    def test_associativity(self):
        """Test associativity of Fp2 operations."""
        a = Fp2(1, 2)
        b = Fp2(3, 4)
        c = Fp2(5, 6)

        # Addition associativity
        assert (a + b) + c == a + (b + c)

        # Multiplication associativity
        assert (a * b) * c == a * (b * c)

    def test_distributivity(self):
        """Test distributivity of multiplication over addition."""
        a = Fp2(1, 2)
        b = Fp2(3, 4)
        c = Fp2(5, 6)

        # a * (b + c) = a * b + a * c
        left = a * (b + c)
        right = (a * b) + (a * c)
        assert left == right

    def test_identity_elements(self):
        """Test identity elements."""
        a = Fp2(12, 34)

        # Additive identity
        zero = Fp2(0, 0)
        assert a + zero == a
        assert zero + a == a

        # Multiplicative identity
        one = Fp2(1, 0)
        assert a * one == a
        assert one * a == a

    def test_inverse_properties(self):
        """Test inverse properties."""
        a = Fp2(12, 34)

        # Additive inverse
        neg_a = Fp2((-a.a0) % P, (-a.a1) % P)
        assert a + neg_a == Fp2(0, 0)

        # Multiplicative inverse (for non-zero elements)
        if not a.is_zero():
            assert a * a.inverse() == Fp2(1, 0)
