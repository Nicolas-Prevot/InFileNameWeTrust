

def is_valid_bmp_char(cp: int) -> bool:
    """
    Check if a codepoint is a valid single-code-unit BMP character for Windows filenames.

    Parameters
    ----------
    cp : int
        The Unicode codepoint.

    Returns
    -------
    bool
        True if valid, False otherwise.
    """
    if cp > 0xFFFF:
        return False
    if cp < 0x20 or cp == 0x7F:  # control chars
        return False
    if 0xD800 <= cp <= 0xDFFF:   # surrogates
        return False
    if 0x0080 <= cp <= 0x00A0:   # Azure
        return False
    if 0xFE00 <= cp <= 0xFE0F:   # Azure
        return False
    if 0xFFF0 <= cp <= 0xFFFC:   # Azure
        return False
    if 0xFD9E <= cp <= 0xFDFA:   # Azure
        return False
    if 0xFF9C <= cp <= 0xFFFD:   # Azure
        return False
    if cp in (0x00AD, 0xFEFF, 0xFFA0):
        return False
    if cp in (0x5C, 0x2F, 0x3A, 0x2A, 0x3F, 0x22, 0x3C, 0x3E, 0x7C):
        return False
    if cp in (0xFFFE, 0xFFFF):
        return False
    if cp in (0x20, 0x2E):       # space, period
        return False
    return True

def build_bmp_singleunit_alphabet():
    """
    Build a string of all valid single-code-unit BMP characters for Windows filenames.

    Returns
    -------
    str
        A string of valid characters.
    """
    chars = []
    for cp in range(0x10000):
        if is_valid_bmp_char(cp):
            chars.append(chr(cp))
    return "".join(chars)
