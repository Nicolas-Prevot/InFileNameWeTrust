import os
import zlib
from loguru import logger
from typing import List, Tuple

class InFileNameStorage:
    """
    A class for encoding and decoding data using zero-byte filenames with a large BMP alphabet.
    """

    def __init__(self, chunk_size: int = 240, max_files_per_part: int = 1000) -> None:
        """
        Initializes the InFileNameStorage instance.

        Parameters
        ----------
        chunk_size : int, optional
            The size of each encoded chunk, by default 240.
        max_files_per_part : int, optional
            Maximum number of files per subfolder, by default 1000.
        """
        self.chunk_size = chunk_size
        self.max_files_per_part = max_files_per_part
        self.alphabet = self._build_bmp_singleunit_alphabet()

        self.base_size = len(self.alphabet)
        self.chunk_bits = 0
        while (1 << self.chunk_bits) <= self.base_size:
            self.chunk_bits += 1
        self.chunk_bits -= 1  # now 2^(chunk_bits) <= base_size
        
        self.char_to_value = {}
        for i, ch in enumerate(self.alphabet):
            if i < (1 << self.chunk_bits):
                self.char_to_value[ch] = i
        
        self.mask = (1 << self.chunk_bits) - 1  # e.g. 0x7FFF for 15 bits

    def _is_valid_bmp_char(self, cp: int) -> bool:
        """
        Determines if a given Unicode code point is valid for filenames on Windows.

        Parameters
        ----------
        cp : int
            The Unicode code point.

        Returns
        -------
        bool
            True if valid, False otherwise.
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

    def _build_bmp_singleunit_alphabet(self) -> str:
        """
        Builds a string of valid BMP characters suitable for encoding filenames.

        Returns
        -------
        str
            A string containing valid BMP characters.
        """
        return "".join(chr(cp) for cp in range(0x10000) if self._is_valid_bmp_char(cp))

    def _encode_bytes_to_bigbase_old(self, data_bytes: bytes) -> str:
        """
        Encodes a byte sequence into a custom large-base string using the BMP alphabet.

        Parameters
        ----------
        data_bytes : bytes
            The input byte data.

        Returns
        -------
        str
            The encoded string.
        """
        base = len(self.alphabet)
        if base < 2:
            raise ValueError("Alphabet size must be >= 2.")

        big_int = int.from_bytes(data_bytes, byteorder="big", signed=False)
        if big_int == 0:
            return self.alphabet[0]

        digits = []
        while big_int > 0:
            if len(digits)%100 == 0: print(len(digits))
            big_int, r = divmod(big_int, base)
            digits.append(self.alphabet[r])

        return "".join(reversed(digits))

    def _encode_bytes_to_bigbase(self, data_bytes: bytes) -> str:
        """
        Encodes a byte sequence into a custom large-base string using the BMP alphabet.

        Parameters
        ----------
        data_bytes : bytes
            The input byte data.

        Returns
        -------
        str
            The encoded string.
        """
        big_int = int.from_bytes(data_bytes, byteorder="big", signed=False)
        if big_int == 0:
            # represent zero as a single digit
            return self.alphabet[0]

        digits = []
        while big_int > 0:
            if len(digits)%100 == 0: print(len(digits))
            remainder = big_int & self.mask
            big_int >>= self.chunk_bits
            # remainder < 2^(chunk_bits) <= base_size => valid index
            digits.append(self.alphabet[remainder])

        digits.reverse()
        return "".join(digits)
    
    def _decode_bigbase_to_bytes(self, encoded_str: str) -> bytes:
        """
        Decodes a custom large-base string back into bytes.

        Parameters
        ----------
        encoded_str : str
            The encoded string.

        Returns
        -------
        bytes
            The decoded byte sequence.
        """
        big_int = 0
        for ch in encoded_str:
            if ch not in self.char_to_value:
                raise ValueError(f"Character {repr(ch)} not in valid subset.")
            remainder = self.char_to_value[ch]
            big_int = (big_int << self.chunk_bits) | remainder

        # Convert big_int to bytes
        byte_len = (big_int.bit_length() + 7) // 8
        return big_int.to_bytes(byte_len, byteorder="big", signed=False)

    def _decode_bigbase_to_bytes_old(self, encoded_str: str) -> bytes:
        """
        Decodes a custom large-base string back into bytes.

        Parameters
        ----------
        encoded_str : str
            The encoded string.

        Returns
        -------
        bytes
            The decoded byte sequence.
        """
        base = len(self.alphabet)
        lookup = {ch: i for i, ch in enumerate(self.alphabet)}

        big_int = 0
        for ch in encoded_str:
            if ch not in lookup:
                raise ValueError(f"Invalid character in encoded string: {repr(ch)}")
            big_int = big_int * base + lookup[ch]

        return big_int.to_bytes((big_int.bit_length() + 7) // 8, byteorder="big", signed=False)

    def encode_file_to_filenames(self, input_file: str, base_output_dir: str) -> None:
        """
        Encodes a file's contents into zero-byte filenames.

        Parameters
        ----------
        input_file : str
            Path to the input file.
        base_output_dir : str
            Directory where encoded filenames will be stored.
        """
        base_name = os.path.basename(input_file)
        name, ext = os.path.splitext(base_name)
        modified_name = f"{name}_{ext.lstrip('.')}"
        main_folder = os.path.join(base_output_dir, modified_name)
        os.makedirs(main_folder, exist_ok=True)

        with open(input_file, "rb") as f:
            original_data = f.read()

        logger.info(f"Read {len(original_data)} bytes from '{input_file}'")

        compressed_data = zlib.compress(original_data, level=9)
        encoded_str = self._encode_bytes_to_bigbase(compressed_data)

        chunks = [encoded_str[i: i + self.chunk_size] for i in range(0, len(encoded_str), self.chunk_size)]
        total_chunks = len(chunks)

        current_part_index = 0
        file_count_in_part = 0

        for i, chunk_data in enumerate(chunks):
            if i % self.max_files_per_part == 0:
                current_part_index += 1
                file_count_in_part = 0
                part_folder_path = os.path.join(main_folder, f"part_{current_part_index:05d}")
                os.makedirs(part_folder_path, exist_ok=True)

            filename = f"{file_count_in_part:03d}_{chunk_data}"
            filepath = os.path.join(main_folder, f"part_{current_part_index:05d}", filename)

            with open(filepath, "wb"):
                pass

            file_count_in_part += 1

        logger.info(f"Created {total_chunks} chunk files in '{main_folder}' across {current_part_index} part folder(s).")


    def decode_filenames_to_file(self, main_folder: str, output_file: str) -> None:
        """
        Decodes zero-byte filenames back into the original file.

        Parameters
        ----------
        main_folder : str
            Directory containing encoded filenames.
        output_file : str
            Path to save the decoded file.

        Raises
        ------
        ValueError
            If no valid chunk files are found in the directory.
        """
        # Gather all (part_idx, file_idx, chunk_data)
        all_entries: List[Tuple[int, int, str]] = []

        for entry in os.scandir(main_folder):
            if entry.is_dir() and entry.name.startswith("part_"):
                part_str = entry.name[5:]  # Extract part number from "part_00001"
                try:
                    pidx = int(part_str)
                except ValueError:
                    continue  # Skip non-numeric parts

                for f in os.scandir(entry.path):
                    if f.is_file():
                        parts = f.name.split('_', 1)
                        if len(parts) == 2:
                            file_idx_str, chunk_data = parts
                            try:
                                fidx = int(file_idx_str)
                                all_entries.append((pidx, fidx, chunk_data))
                            except ValueError:
                                continue  # Skip invalid file names

        # Sort entries first by part index, then by file index
        all_entries.sort()

        if not all_entries:
            raise ValueError(f"No valid chunk files found under '{main_folder}'")

        # Reassemble the encoded data
        bigbase_str = "".join(chunk_data for _, _, chunk_data in all_entries)
        compressed_data = self._decode_bigbase_to_bytes(bigbase_str)
        original_data = zlib.decompress(compressed_data)

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "wb") as out_f:
            out_f.write(original_data)

        logger.info(f"Decoded and wrote {len(original_data)} bytes into '{output_file}'.")

    """def decode_filenames_to_file_old(self, main_folder, output_file):
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

        logger.info(f"Decoded and wrote {len(original_data)} bytes into '{output_file}'.")"""
    
    