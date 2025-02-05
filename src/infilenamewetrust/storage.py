import os
import zlib
from loguru import logger
import re

class InFileNameStorage:
    """
    A class encapsulating the logic to encode/decode data
    in zero-byte filenames using a large BMP alphabet.
    """

    def __init__(self, chunk_size=240, max_files_per_part=1000):
        self.chunk_size = chunk_size
        self.max_files_per_part = max_files_per_part
        self.alphabet = self._build_bmp_singleunit_alphabet()

    def _is_valid_bmp_char(self, cp):
        """
        Returns True if 'cp' (integer) is a valid BMP character for Windows
        filenames, occupying exactly 1 UTF-16 code unit (i.e., [0..0xFFFF]).
        """
        if cp > 0xFFFF:
            return False

        # Skip control chars < 0x20 and 0x7F
        if cp < 0x20 or cp == 0x7F:
            return False

        # Skip surrogate range [0xD800..0xDFFF]
        if 0xD800 <= cp <= 0xDFFF:
            return False

        # Skip Windows reserved punctuation: \ / : * ? " < > |
        if cp in (0x5C, 0x2F, 0x3A, 0x2A, 0x3F, 0x22, 0x3C, 0x3E, 0x7C):
            return False

        # Skip noncharacters in BMP: 0xFFFE, 0xFFFF
        if cp in (0xFFFE, 0xFFFF):
            return False

        # Also skip space (0x20) and period (0x2E) to avoid trailing/leading issues
        if cp in (0x20, 0x2E):
            return False

        return True

    def _build_bmp_singleunit_alphabet(self):
        """
        Builds a list/string of BMP characters (U+0000..U+FFFF) that are each
        exactly 1 UTF-16 code unit, skipping those invalid for filenames.
        """
        valid_chars = []
        for cp in range(0x0000, 0x10000):  # up to 0xFFFF
            if self._is_valid_bmp_char(cp):
                valid_chars.append(chr(cp))
        return "".join(valid_chars)

    def _encode_bytes_to_bigbase(self, data_bytes):
        """
        1. Interpret data_bytes as a large integer (big-endian).
        2. Convert that integer to base-N (N = len(self.alphabet)).
        """
        base = len(self.alphabet)
        if base < 2:
            raise ValueError("Alphabet size must be >= 2.")

        big_int = int.from_bytes(data_bytes, byteorder="big", signed=False)
        if big_int == 0:
            return self.alphabet[0]  # Single 'digit' for zero

        digits = []
        while big_int > 0:
            big_int, r = divmod(big_int, base)
            digits.append(self.alphabet[r])

        digits.reverse()
        return "".join(digits)

    def _decode_bigbase_to_bytes(self, encoded_str):
        """
        1. Convert each character to its digit in the custom base.
        2. Accumulate a big integer.
        3. Convert that integer to bytes (big-endian).
        """
        base = len(self.alphabet)
        lookup = {ch: i for i, ch in enumerate(self.alphabet)}

        big_int = 0
        for ch in encoded_str:
            if ch not in lookup:
                raise ValueError(f"Invalid character in encoded string: {repr(ch)}")
            big_int = big_int * base + lookup[ch]

        byte_len = (big_int.bit_length() + 7) // 8
        return big_int.to_bytes(byte_len, byteorder="big", signed=False)

    def encode_file_to_filenames(self, input_file, base_output_dir):

        base_name = os.path.basename(input_file)
        main_folder = os.path.join(base_output_dir, base_name)
        os.makedirs(main_folder, exist_ok=True)

        # Read & compress
        with open(input_file, "rb") as f:
            original_data = f.read()
        logger.info(f"Read {len(original_data)} bytes from '{input_file}'")

        compressed_data = zlib.compress(original_data, level=9)
        logger.info(f"Compressed to {len(compressed_data)} bytes")

        # Encode
        encoded_str = self._encode_bytes_to_bigbase(compressed_data)
        logger.info(f"Encoded length: {len(encoded_str)} characters")

        # Split into chunks
        chunks = [
            encoded_str[i : i + self.chunk_size]
            for i in range(0, len(encoded_str), self.chunk_size)
        ]
        total_chunks = len(chunks)

        # Create subfolders each containing up to max_files_per_part
        current_part_index = 0  # for naming "part_00001", etc.
        file_count_in_part = 0

        for i, chunk_data in enumerate(chunks):
            # If we've filled up a part folder or if none created yet, move to next part
            if i % self.max_files_per_part == 0:
                current_part_index += 1
                file_count_in_part = 0
                part_folder_name = f"part_{current_part_index:05d}"
                part_folder_path = os.path.join(main_folder, part_folder_name)
                os.makedirs(part_folder_path, exist_ok=True)
                logger.debug(f"Created/using folder: {part_folder_path}")

            # file_count_in_part is the index within the part
            filename_index = f"{file_count_in_part:03d}"
            filename = f"{filename_index}_{chunk_data}"
            filepath = os.path.join(
                main_folder, 
                f"part_{current_part_index:05d}",
                filename
            )
            with open(filepath, "wb"):
                pass

            file_count_in_part += 1

        logger.info(
            f"Created {total_chunks} chunk files in '{main_folder}' "
            f"across {current_part_index} part folder(s)."
        )

    def decode_filenames_to_file(self, main_folder, output_file):
        part_pattern = re.compile(r"^part_(\d{5})$")
        file_pattern = re.compile(r"^(\d{3})_(.+)$")

        # Collect part folders
        parts = []
        for entry in os.scandir(main_folder):
            if entry.is_dir():
                m = part_pattern.match(entry.name)
                if m:
                    part_idx = int(m.group(1))
                    parts.append((part_idx, entry.path))
        parts.sort(key=lambda x: x[0])  # sort by numeric part index

        if not parts:
            raise ValueError(f"No 'part_XXXXX' subfolders found in '{main_folder}'")

        # Collect chunk data from each part in order
        all_chunks = []
        for _, part_path in parts:
            # Gather all files
            chunk_files = []
            for fentry in os.scandir(part_path):
                if fentry.is_file():
                    m2 = file_pattern.match(fentry.name)
                    if m2:
                        file_idx = int(m2.group(1))
                        chunk_data = m2.group(2)
                        chunk_files.append((file_idx, chunk_data))

            # Sort by the 3-digit file index
            chunk_files.sort(key=lambda x: x[0])
            for _, cdata in chunk_files:
                all_chunks.append(cdata)

        if not all_chunks:
            raise ValueError(f"No valid chunk files found under '{main_folder}'")

        # Reassemble the big-base string
        bigbase_str = "".join(all_chunks)

        # Decode
        compressed_data = self._decode_bigbase_to_bytes(bigbase_str)
        original_data = zlib.decompress(compressed_data)

        # Ensure the output folder exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "wb") as out_f:
            out_f.write(original_data)

        logger.info(f"Decoded and wrote {len(original_data)} bytes into '{output_file}'.")
    
    def decode_filenames_to_file_v2(self, main_folder, output_file):
        """
        This is a revised version of decode, avoiding regex:
        1) Each subfolder = 'part_00001', etc. => parse last 5 digits for the part index.
        2) Each file = '000_<chunk>' => parse first 3 digits for file index, then rest for chunk.
        """
        # Gather all (part_idx, file_idx, chunk_data)
        all_entries = []
        for entry in os.scandir(main_folder):
            if entry.is_dir() and entry.name.startswith("part_"):
                part_str = entry.name[5:]  # e.g. "00001"
                try:
                    pidx = int(part_str)
                except ValueError:
                    continue  # skip non-numeric
                for f in os.scandir(entry.path):
                    if f.is_file():
                        splitted = f.name.split('_', 1)
                        if len(splitted) == 2:
                            file_idx_str, chunk_data = splitted
                            try:
                                fidx = int(file_idx_str)
                            except ValueError:
                                continue
                            all_entries.append((pidx, fidx, chunk_data))

        # Sort: first by pidx, then by fidx
        all_entries.sort(key=lambda x: (x[0], x[1]))

        if not all_entries:
            raise ValueError(f"No valid chunk files found under '{main_folder}'")

        # Re-assemble
        bigbase_str = "".join(chunk_data for (_, _, chunk_data) in all_entries)
        compressed_data = self._decode_bigbase_to_bytes(bigbase_str)
        original_data = zlib.decompress(compressed_data)

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "wb") as out_f:
            out_f.write(original_data)

        logger.info(f"Decoded and wrote {len(original_data)} bytes into '{output_file}'.")
