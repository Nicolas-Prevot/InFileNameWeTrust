# cython: language_level=3
import cython

@cython.boundscheck(False)
@cython.wraparound(False)
def encode(bytes data, int chunk_bits, str alphabet) -> str:
    """
    Encode the input bytes into a string using a custom alphabet.

    Parameters
    ----------
    data : bytes
        The input bytes (e.g. compressed data).
    chunk_bits : int
        Number of bits per “digit” (i.e. base = 2^chunk_bits).
    alphabet : str
        A string of allowed characters (only the first 2^chunk_bits characters are used).

    Returns
    -------
    str
        A string where each character encodes `chunk_bits` of the input bitstream.
    """
    cdef:
        int data_len = len(data)
        int i
        unsigned int bit_buffer = 0
        int bit_count = 0
        int digit
        int base = 1 << chunk_bits   # base is 2^chunk_bits
        list result = []
    # Use a memory view to ensure we get unsigned values
    cdef const unsigned char* d = data
    for i in range(data_len):
        # Ensure the byte is in 0-255 range
        bit_buffer = (bit_buffer << 8) | (d[i] & 0xFF)
        bit_count += 8
        # While we have enough bits for one chunk, extract a digit.
        while bit_count >= chunk_bits:
            digit = (bit_buffer >> (bit_count - chunk_bits)) & (base - 1)
            result.append(alphabet[digit])
            bit_count -= chunk_bits
    if bit_count > 0:
        # If any bits remain, pad them on the right with zeros to form one last digit.
        digit = (bit_buffer << (chunk_bits - bit_count)) & (base - 1)
        result.append(alphabet[digit])
    return "".join(result)

@cython.boundscheck(False)
@cython.wraparound(False)
def decode(str encoded, int chunk_bits, reverse_map) -> bytes:
    """
    Decode a string produced by `encode` back into the original bytes.

    Parameters
    ----------
    encoded : str
        The encoded string (each character represents `chunk_bits` bits).
    chunk_bits : int
        The number of bits per encoded character.
    reverse_map : dict
        Mapping from valid alphabet characters to their integer values.

    Returns
    -------
    bytes
        The decoded bytes. (Extra padding bits must be trimmed by the caller.)
    """
    cdef:
        int encoded_len = len(encoded)
        unsigned int bit_buffer = 0
        int bit_count = 0
        int base = 1 << chunk_bits   # base = 2^chunk_bits
        int digit
        int i
        list byte_array = []
        unsigned int byte_val
    for i in range(encoded_len):
        # Look up the integer value for this character.
        digit = reverse_map[encoded[i]]
        # Add the digit’s bits to the bit_buffer.
        bit_buffer = (bit_buffer << chunk_bits) | digit
        bit_count += chunk_bits
        # While we have at least 8 bits, extract a byte.
        while bit_count >= 8:
            byte_val = (bit_buffer >> (bit_count - 8)) & 0xFF
            byte_array.append(byte_val)
            bit_count -= 8
    # Any leftover bits (which are just padding) are ignored.
    return bytes(byte_array)
