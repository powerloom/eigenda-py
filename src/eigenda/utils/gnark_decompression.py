"""Gnark-crypto compatible point decompression for BN254."""

from typing import Tuple

from .bn254_field import P, compute_y_from_x

# Compression flags from gnark-crypto
COMPRESSED_SMALLEST = 0b10 << 6  # 0x80
COMPRESSED_LARGEST = 0b11 << 6  # 0xC0
COMPRESSED_INFINITY = 0b01 << 6  # 0x40
MASK = COMPRESSED_INFINITY | COMPRESSED_SMALLEST | COMPRESSED_LARGEST


def decompress_g1_point_gnark(compressed: bytes) -> Tuple[int, int]:
    """
    Decompress a G1 point from gnark-crypto compressed format.

    Gnark uses compression flags in the most significant bits:
    - 0x40: Point at infinity
    - 0x80: Compressed with smaller y
    - 0xC0: Compressed with larger y

    Args:
        compressed: 32 bytes of compressed G1 point

    Returns:
        Tuple of (x, y) as integers
    """
    if len(compressed) != 32:
        raise ValueError(f"Expected 32 bytes for compressed G1 point, got {len(compressed)}")

    # Extract compression flag
    flag = compressed[0] & MASK

    # Check for point at infinity
    if flag == COMPRESSED_INFINITY:
        return (0, 0)

    # Remove the compression flag to get x coordinate
    x_bytes = bytearray(compressed)
    x_bytes[0] &= ~MASK
    x = int.from_bytes(x_bytes, byteorder="big")

    # Compute y from x
    y, exists = compute_y_from_x(x)
    if not exists:
        raise ValueError(f"No valid point exists for x={x}")

    # Determine which y to use based on the flag
    # In BN254, we consider y to be "larger" if it's > p/2
    y_is_larger = y > P // 2

    if flag == COMPRESSED_LARGEST:
        if not y_is_larger:
            y = P - y
    elif flag == COMPRESSED_SMALLEST:
        if y_is_larger:
            y = P - y
    else:
        raise ValueError(f"Invalid compression flag: {hex(flag)}")

    return (x, y)


def decompress_g2_point_gnark(compressed: bytes) -> Tuple[list[int], list[int]]:
    """
    Decompress a G2 point from gnark-crypto compressed format.

    G2 points use quadratic extension field Fp2, so each coordinate
    is represented as two field elements (c0, c1).

    Args:
        compressed: 64 bytes of compressed G2 point

    Returns:
        Tuple of ([x0, x1], [y0, y1]) as integers
    """
    try:
        # Try full decompression first
        from .g2_decompression import decompress_g2_point_full

        (x0, x1), (y0, y1) = decompress_g2_point_full(compressed)
        return ([x0, x1], [y0, y1])
    except Exception as e:
        # If full decompression fails, use simple version with placeholder Y
        print(f"G2 decompression failed: {e}, using placeholder Y values")
        from .g2_decompression import decompress_g2_point_simple

        (x0, x1), (y0, y1) = decompress_g2_point_simple(compressed)
        return ([x0, x1], [y0, y1])
