# cython: language_level=3

def encode_chunk_py(bytes_in: bytes, int chunk_bits, str alphabet) -> str:
    """
    Cython-accelerated function to encode 'bytes_in' by packing 'chunk_bits'
    bits at a time into indices that map to 'alphabet'.
    We only use the first 2^chunk_bits characters of 'alphabet'.
    """
    cdef int mask = (1 << chunk_bits) - 1
    cdef int alph_len = len(alphabet)

    cdef unsigned long long bit_buffer = 0
    cdef int bits_in_buffer = 0

    # Pre-declare C variables for use inside loops
    cdef int index
    cdef unsigned char c

    # We'll collect output in a Python list, then join at the end
    cdef list output_chars = []

    # Loop over each byte in 'bytes_in'
    for c in bytes_in:
        bit_buffer = (bit_buffer << 8) | c
        bits_in_buffer += 8

        # Extract as many chunk_bits as possible
        while bits_in_buffer >= chunk_bits:
            bits_in_buffer -= chunk_bits
            index = int((bit_buffer >> bits_in_buffer) & mask)
            output_chars.append(alphabet[index])

    # Leftover bits
    if bits_in_buffer > 0:
        index = int(bit_buffer & ((1 << bits_in_buffer) - 1))
        output_chars.append(alphabet[index])

    return "".join(output_chars)


def decode_chunk_py(str encoded_str, int chunk_bits, dict reverse_map) -> bytes:
    """
    Reverse of encode_chunk_py. 'reverse_map' is a dict from character -> int index,
    which must match the first 2^chunk_bits characters used in 'alphabet'.
    """
    cdef int mask = (1 << chunk_bits) - 1
    cdef unsigned long long bit_buffer = 0
    cdef int bits_in_buffer = 0

    # We'll collect output in a Python bytearray, then convert to bytes
    cdef bytearray out_bytes = bytearray()

    # Pre-declare variables used in loops
    cdef int val
    cdef unsigned char b
    cdef Py_ssize_t i, n = len(encoded_str)
    cdef char ch

    for i in range(n):
        ch = encoded_str[i]
        if ch not in reverse_map:
            raise ValueError(f"Invalid character {repr(ch)} in decode map.")
        val = reverse_map[ch]

        bit_buffer = (bit_buffer << chunk_bits) | val
        bits_in_buffer += chunk_bits

        # Produce full bytes while possible
        while bits_in_buffer >= 8:
            bits_in_buffer -= 8
            b = (bit_buffer >> bits_in_buffer) & 0xFF
            out_bytes.append(b)

    # If leftover bits remain, treat them as one partial byte
    if bits_in_buffer > 0:
        b = bit_buffer & ((1 << bits_in_buffer) - 1)
        out_bytes.append(b)

    return bytes(out_bytes)
