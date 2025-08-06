"""BN254 Fp2 (quadratic extension field) arithmetic utilities."""

from typing import Tuple

# BN254 field modulus
P = 21888242871839275222246405745257275088696311157297823662689037894645226208583

# Fp2 is defined as Fp[u]/(u^2 + 1), so u^2 = -1
# Elements are represented as a0 + a1*u where a0, a1 are in Fp


class Fp2:
    """Element in the quadratic extension field Fp2."""

    def __init__(self, a0: int, a1: int):
        """Create Fp2 element a0 + a1*u."""
        self.a0 = a0 % P
        self.a1 = a1 % P

    def __add__(self, other: "Fp2") -> "Fp2":
        """Add two Fp2 elements."""
        return Fp2((self.a0 + other.a0) % P, (self.a1 + other.a1) % P)

    def __sub__(self, other: "Fp2") -> "Fp2":
        """Subtract two Fp2 elements."""
        return Fp2((self.a0 - other.a0) % P, (self.a1 - other.a1) % P)

    def __mul__(self, other: "Fp2") -> "Fp2":
        """
        Multiply two Fp2 elements.
        (a0 + a1*u) * (b0 + b1*u) = (a0*b0 - a1*b1) + (a0*b1 + a1*b0)*u
        Since u^2 = -1
        """
        return Fp2(
            (self.a0 * other.a0 - self.a1 * other.a1) % P,
            (self.a0 * other.a1 + self.a1 * other.a0) % P,
        )

    def square(self) -> "Fp2":
        """
        Square an Fp2 element.
        (a0 + a1*u)^2 = (a0^2 - a1^2) + 2*a0*a1*u
        """
        return Fp2((self.a0 * self.a0 - self.a1 * self.a1) % P, (2 * self.a0 * self.a1) % P)

    def conjugate(self) -> "Fp2":
        """Return conjugate a0 - a1*u."""
        return Fp2(self.a0, (-self.a1) % P)

    def inverse(self) -> "Fp2":
        """
        Compute multiplicative inverse.
        1/(a0 + a1*u) = (a0 - a1*u)/(a0^2 + a1^2)
        """
        norm = (self.a0 * self.a0 + self.a1 * self.a1) % P
        norm_inv = pow(norm, P - 2, P)  # Fermat's little theorem
        conj = self.conjugate()
        return Fp2((conj.a0 * norm_inv) % P, (conj.a1 * norm_inv) % P)

    def __eq__(self, other: "Fp2") -> bool:
        """Check equality."""
        return self.a0 == other.a0 and self.a1 == other.a1

    def is_zero(self) -> bool:
        """Check if element is zero."""
        return self.a0 == 0 and self.a1 == 0

    def legendre(self) -> int:
        """
        Compute Legendre symbol in Fp2.
        Returns 1 if element is a quadratic residue, -1 if not.
        """
        # For Fp2, we use the norm map to Fp
        norm = (self.a0 * self.a0 + self.a1 * self.a1) % P
        return pow(norm, (P - 1) // 2, P)

    def __repr__(self) -> str:
        return f"Fp2({self.a0}, {self.a1})"


def sqrt_fp2(a: Fp2) -> Tuple[Fp2, bool]:
    """
    Compute square root in Fp2.

    This uses the complex square root algorithm adapted for Fp2.

    Args:
        a: Element to find square root of

    Returns:
        (sqrt, exists) where sqrt^2 = a if exists is True
    """
    if a.is_zero():
        return (Fp2(0, 0), True)

    # Algorithm from "Square roots from 1; 24, 51, 10 to Dan Shanks" by Tonelli and Shanks
    # Adapted for quadratic extension fields

    # First check if a is a quadratic residue
    if a.legendre() != 1:
        return (Fp2(0, 0), False)

    # Special case for p ≡ 3 (mod 4), which BN254 satisfies
    # We can use a simpler algorithm

    # Try to find alpha such that alpha^2 = a
    # For Fp2, we can use the formula from complex numbers

    # If a = a0 + a1*u, we want to find x0 + x1*u such that:
    # (x0 + x1*u)^2 = a0 + a1*u
    # x0^2 - x1^2 = a0
    # 2*x0*x1 = a1

    # Let's compute |a| = sqrt(a0^2 + a1^2) in Fp
    norm_squared = (a.a0 * a.a0 + a.a1 * a.a1) % P

    # We need sqrt of norm_squared in Fp
    # Using Tonelli-Shanks for Fp
    norm = tonelli_shanks_fp(norm_squared)
    if norm is None:
        return (Fp2(0, 0), False)

    # Now we can compute x0 and x1
    # x0 = sqrt((a0 + |a|) / 2)
    # x1 = a1 / (2 * x0)

    # First compute (a0 + norm) / 2
    half = pow(2, P - 2, P)  # multiplicative inverse of 2
    x0_squared = ((a.a0 + norm) * half) % P

    x0 = tonelli_shanks_fp(x0_squared)
    if x0 is None:
        # Try the other square root
        x0_squared = ((a.a0 - norm) * half) % P
        x0 = tonelli_shanks_fp(x0_squared)
        if x0 is None:
            return (Fp2(0, 0), False)

    # Compute x1 = a1 / (2 * x0)
    if x0 == 0:
        # Special case: a must be negative real number
        # x = sqrt(-|a0|) * u
        x1_squared = (-a.a0) % P
        x1 = tonelli_shanks_fp(x1_squared)
        if x1 is None:
            return (Fp2(0, 0), False)
        result = Fp2(0, x1)
    else:
        two_x0_inv = pow(2 * x0, P - 2, P)
        x1 = (a.a1 * two_x0_inv) % P
        result = Fp2(x0, x1)

    # Verify the result
    check = result.square()
    if check == a:
        return (result, True)

    # Try the negative
    result = Fp2((-result.a0) % P, (-result.a1) % P)
    check = result.square()
    if check == a:
        return (result, True)

    return (Fp2(0, 0), False)


def tonelli_shanks_fp(n: int) -> int:
    """
    Compute square root in Fp using Tonelli-Shanks.
    Returns None if no square root exists.
    """
    n = n % P

    # Check if n is a quadratic residue
    if pow(n, (P - 1) // 2, P) != 1:
        return None

    # Special case
    if n == 0:
        return 0

    # Find Q and S such that P - 1 = Q * 2^S with Q odd
    Q = P - 1
    S = 0
    while Q % 2 == 0:
        Q //= 2
        S += 1

    # Find a quadratic non-residue z
    z = 2
    while pow(z, (P - 1) // 2, P) != P - 1:
        z += 1

    # Initialize variables
    M = S
    c = pow(z, Q, P)
    t = pow(n, Q, P)
    R = pow(n, (Q + 1) // 2, P)

    while True:
        if t == 0:
            return 0
        if t == 1:
            return R

        # Find the least i such that t^(2^i) = 1
        i = 1
        t_pow = t
        while i < M:
            t_pow = pow(t_pow, 2, P)
            if t_pow == 1:
                break
            i += 1

        # Update variables
        b = pow(c, 1 << (M - i - 1), P)
        M = i
        c = pow(b, 2, P)
        t = (t * c) % P
        R = (R * b) % P
