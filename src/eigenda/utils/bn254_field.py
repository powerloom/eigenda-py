"""BN254 field arithmetic utilities."""

# BN254 field modulus
P = 21888242871839275222246405745257275088696311157297823662689037894645226208583


def compute_y_from_x(x: int) -> tuple[int, bool]:
    """
    Compute y coordinate from x coordinate on BN254 curve.

    The curve equation is: y^2 = x^3 + 3

    Args:
        x: The x coordinate as an integer

    Returns:
        Tuple of (y, exists) where y is the positive y coordinate
        and exists indicates if a valid point exists
    """
    # Calculate y^2 = x^3 + 3 (mod p)
    y_squared = (pow(x, 3, P) + 3) % P

    # Check if y_squared is a quadratic residue
    legendre = pow(y_squared, (P - 1) // 2, P)
    if legendre != 1:
        return (0, False)

    # Compute square root using Tonelli-Shanks
    y = tonelli_shanks(y_squared, P)
    if y is None:
        return (0, False)

    # Return the smaller of the two possible y values (convention)
    if y > P // 2:
        y = P - y

    return (y, True)


def tonelli_shanks(n: int, p: int) -> int:
    """
    Find r such that r^2 = n (mod p) using the Tonelli-Shanks algorithm.

    Returns None if no square root exists.
    """
    # Check if n is a quadratic residue
    if pow(n, (p - 1) // 2, p) != 1:
        return None

    # Find Q and S such that p - 1 = Q * 2^S with Q odd
    Q = p - 1
    S = 0
    while Q % 2 == 0:
        Q //= 2
        S += 1

    # Find a quadratic non-residue z
    z = 2
    while pow(z, (p - 1) // 2, p) != p - 1:
        z += 1

    # Initialize variables
    M = S
    c = pow(z, Q, p)
    t = pow(n, Q, p)
    R = pow(n, (Q + 1) // 2, p)

    while True:
        if t == 0:
            return 0
        if t == 1:
            return R

        # Find the least i such that t^(2^i) = 1
        i = 1
        t_pow = t
        while i < M:
            t_pow = pow(t_pow, 2, p)
            if t_pow == 1:
                break
            i += 1

        # Update variables
        b = pow(c, 1 << (M - i - 1), p)
        M = i
        c = pow(b, 2, p)
        t = (t * c) % p
        R = (R * b) % p
