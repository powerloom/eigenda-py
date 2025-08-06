"""G2 point decompression for BN254."""

from typing import Tuple

from .fp2_arithmetic import Fp2, P, sqrt_fp2

# BN254 G2 curve: y^2 = x^3 + b where b is in Fp2
# b = (19485874751759354771024239261021720505790618469301721065564631296452457478373,
#      266929791119991161246907387137283842545076965332900288569378510910307636690)
B_A0 = 19485874751759354771024239261021720505790618469301721065564631296452457478373
B_A1 = 266929791119991161246907387137283842545076965332900288569378510910307636690

# Compression flags from gnark-crypto
COMPRESSED_SMALLEST = 0b10 << 6  # 0x80
COMPRESSED_LARGEST = 0b11 << 6  # 0xC0
COMPRESSED_INFINITY = 0b01 << 6  # 0x40
MASK = COMPRESSED_INFINITY | COMPRESSED_SMALLEST | COMPRESSED_LARGEST


def decompress_g2_point_full(compressed: bytes) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """
    Decompress a G2 point from gnark-crypto compressed format.

    G2 points use quadratic extension field Fp2, so each coordinate
    is represented as two field elements (c0, c1).

    Args:
        compressed: 64 bytes of compressed G2 point

    Returns:
        Tuple of ((x0, x1), (y0, y1)) as integers
    """
    if len(compressed) != 64:
        raise ValueError(f"Expected 64 bytes for compressed G2 point, got {len(compressed)}")

    # Extract compression flag from first byte
    flag = compressed[0] & MASK

    # Check for point at infinity
    if flag == COMPRESSED_INFINITY:
        return ((0, 0), (0, 0))

    # Remove compression flag
    x_bytes = bytearray(compressed)
    x_bytes[0] &= ~MASK

    # Extract X coordinates (note the ordering: x1 comes first, then x0)
    # This matches gnark serialization
    x1 = int.from_bytes(x_bytes[0:32], byteorder="big")
    x0 = int.from_bytes(x_bytes[32:64], byteorder="big")

    # Create Fp2 element for x
    x = Fp2(x0, x1)

    # Compute y^2 = x^3 + b
    x_squared = x.square()
    x_cubed = x_squared * x
    b = Fp2(B_A0, B_A1)
    y_squared = x_cubed + b

    # Compute square root
    y, exists = sqrt_fp2(y_squared)
    if not exists:
        raise ValueError(f"No valid G2 point exists for x=({x0}, {x1})")

    # Determine which y to use based on the flag
    # For G2 in Fp2, we need to determine "lexicographically larger"
    # Following gnark's convention: check y.a1 first, then y.a0
    y_is_larger = False
    if y.a1 > P // 2:
        y_is_larger = True
    elif y.a1 == 0 and y.a0 > P // 2:
        y_is_larger = True

    # Adjust y based on compression flag
    if flag == COMPRESSED_LARGEST:
        if not y_is_larger:
            y = Fp2((-y.a0) % P, (-y.a1) % P)
    elif flag == COMPRESSED_SMALLEST:
        if y_is_larger:
            y = Fp2((-y.a0) % P, (-y.a1) % P)
    else:
        # No compression flag, might be a different format
        # For now, just use the computed y
        pass

    return ((x0, x1), (y.a0, y.a1))


def decompress_g2_point_simple(compressed: bytes) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """
    Simple G2 decompression that returns placeholder Y values.

    This is a fallback if full decompression fails.
    """
    if len(compressed) != 64:
        raise ValueError(f"Expected 64 bytes for compressed G2 point, got {len(compressed)}")

    # Extract X coordinates
    x1 = int.from_bytes(compressed[0:32], byteorder="big")
    x0 = int.from_bytes(compressed[32:64], byteorder="big")

    # Return with placeholder Y values
    return ((x0, x1), (0, 0))
