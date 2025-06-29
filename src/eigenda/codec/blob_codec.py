"""Blob data encoding and decoding functions."""

# Constants from the Go implementation
BYTES_PER_SYMBOL = 32
BYTES_PER_FIELD_ELEMENT = 31

# BN254 field modulus
BN254_MODULUS = 21888242871839275222246405745257275088548364400416034343698204186575808495617


def encode_blob_data(data: bytes) -> bytes:
    """
    Encode raw data for dispersal by padding empty bytes.
    
    Takes bytes and inserts an empty byte at the front of every 31 bytes.
    The empty byte is padded at the low address (big endian).
    This ensures every 32 bytes is within the valid range of a field element for bn254 curve.
    
    Args:
        data: Raw data to encode
        
    Returns:
        Encoded data ready for dispersal
    """
    if len(data) == 0:
        return b''
    
    data_size = len(data)
    parse_size = BYTES_PER_FIELD_ELEMENT  # 31
    put_size = BYTES_PER_SYMBOL  # 32
    
    # Calculate number of chunks needed
    num_chunks = (data_size + parse_size - 1) // parse_size
    
    # Allocate output buffer
    encoded = bytearray(num_chunks * put_size)
    valid_end = len(encoded)
    
    for i in range(num_chunks):
        start = i * parse_size
        end = min((i + 1) * parse_size, len(data))
        
        if end > len(data):
            end = len(data)
            # Adjust valid_end for the last partial chunk
            valid_end = (end - start) + 1 + (i * put_size)
        
        # Set first byte to 0 to ensure data is within valid field element range
        encoded[i * BYTES_PER_SYMBOL] = 0x00
        
        # Copy the chunk data
        chunk_data = data[start:end]
        encoded[i * BYTES_PER_SYMBOL + 1 : i * BYTES_PER_SYMBOL + 1 + len(chunk_data)] = chunk_data
    
    return bytes(encoded[:valid_end])


def decode_blob_data(encoded_data: bytes) -> bytes:
    """
    Decode blob data by removing padding bytes.
    
    Takes encoded bytes and removes the first byte from every 32 bytes.
    This reverses the encoding done by encode_blob_data.
    
    Args:
        encoded_data: Encoded blob data
        
    Returns:
        Original raw data
    """
    if len(encoded_data) == 0:
        return b''
    
    decoded = bytearray()
    
    i = 0
    while i < len(encoded_data):
        # Skip the padding byte
        i += 1
        
        # Determine how many bytes to read (up to 31)
        remaining = len(encoded_data) - i
        chunk_size = min(BYTES_PER_FIELD_ELEMENT, remaining)
        
        if chunk_size > 0:
            # Read the chunk
            decoded.extend(encoded_data[i:i + chunk_size])
            i += chunk_size
    
    return bytes(decoded)


def validate_field_element(data: bytes) -> bool:
    """
    Validate that a 32-byte chunk represents a valid BN254 field element.
    
    Args:
        data: 32-byte chunk to validate
        
    Returns:
        True if valid field element, False otherwise
    """
    if len(data) != BYTES_PER_SYMBOL:
        return False
    
    # Convert bytes to integer (big endian)
    value = int.from_bytes(data, byteorder='big')
    
    # Check if within valid range
    return 0 <= value < BN254_MODULUS