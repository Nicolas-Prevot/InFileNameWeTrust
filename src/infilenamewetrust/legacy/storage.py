import os
import zlib
from typing import List, Tuple
from loguru import logger
from tqdm import tqdm

class InFileNameStorage:
    """
    A class for encoding and decoding data using zero-byte filenames with a large BMP alphabet,
    using a faster 'streaming' approach to pack/unpack bits.
    """

    def __init__(self, chunk_size: int = 240, max_files_per_part: int = 1000) -> None:
        """
        Parameters
        ----------
        chunk_size : int, optional
            Number of characters to store in each filename (default=240).
        max_files_per_part : int, optional
            Maximum number of files per subfolder (default=1000).
        """
        self.chunk_size = chunk_size
        self.max_files_per_part = max_files_per_part

        # Build our BMP single-code-unit alphabet
        self.alphabet = self._build_bmp_singleunit_alphabet()
        self.base_size = len(self.alphabet)

        # Determine how many bits we can pack in one "digit"
        # so that 2^(chunk_bits) <= base_size
        self.chunk_bits = 0
        while (1 << self.chunk_bits) <= self.base_size:
            self.chunk_bits += 1
        self.chunk_bits -= 1  # e.g. if base_size ~63k, chunk_bits = 15

        # We'll only use the first 2^(chunk_bits) characters of self.alphabet.
        # Build a reverse lookup for decoding
        self.char_to_value = {}
        for i, ch in enumerate(self.alphabet):
            if i < (1 << self.chunk_bits):
                self.char_to_value[ch] = i

        # A mask for extracting chunk_bits at a time
        self.mask = (1 << self.chunk_bits) - 1

    # -------------------------------------------------------------------------
    # Build the BMP Alphabet
    # -------------------------------------------------------------------------
    def _is_valid_bmp_char(self, cp: int) -> bool:
        """Check if a codepoint is a valid single-code-unit BMP char for Windows filenames."""
        if cp > 0xFFFF:  # Not in BMP
            return False
        if cp < 0x20 or cp == 0x7F:  # control chars
            return False
        if 0xD800 <= cp <= 0xDFFF:   # surrogates
            return False
        if cp in (0x5C, 0x2F, 0x3A, 0x2A, 0x3F, 0x22, 0x3C, 0x3E, 0x7C):
            return False
        if cp in (0xFFFE, 0xFFFF):   # noncharacters
            return False
        if cp in (0x20, 0x2E):       # space, period
            return False
        return True

    def _build_bmp_singleunit_alphabet(self) -> str:
        """Return a string of valid BMP characters for filenames."""
        chars = []
        for cp in range(0x10000):
            if self._is_valid_bmp_char(cp):
                chars.append(chr(cp))
        return "".join(chars)

    # -------------------------------------------------------------------------
    # 1) Streaming Encode: Byte -> Bits -> "Digits"
    # -------------------------------------------------------------------------
    def _encode_streaming(self, data_bytes: bytes) -> str:
        """
        Convert data_bytes into a "base" string by packing self.chunk_bits at a time
        into an integer index, then mapping to a character in self.alphabet.
        Uses a streaming bit-buffer approach to avoid massive big integers.
        """
        # We'll only use the first 2^chunk_bits characters
        sub_alphabet = self.alphabet[:1 << self.chunk_bits]

        bit_buffer = 0
        bits_in_buffer = 0
        out_chars = []

        # Show a progress bar while reading the data
        for b in tqdm(data_bytes, desc="Encoding", unit="B", unit_scale=True):
            bit_buffer = (bit_buffer << 8) | b
            bits_in_buffer += 8

            # Extract as many chunk_bits as possible
            while bits_in_buffer >= self.chunk_bits:
                bits_in_buffer -= self.chunk_bits
                index = (bit_buffer >> bits_in_buffer) & self.mask
                out_chars.append(sub_alphabet[index])

        # If there's leftover bits, produce one last partial digit
        if bits_in_buffer > 0:
            index = bit_buffer & ((1 << bits_in_buffer) - 1)
            out_chars.append(sub_alphabet[index])

        return "".join(out_chars)

    # -------------------------------------------------------------------------
    # 2) Streaming Decode: "Digits" -> Bits -> Byte
    # -------------------------------------------------------------------------
    def _decode_streaming(self, encoded_str: str) -> bytes:
        """
        Reverse of _encode_streaming: read each character, map to an integer,
        shift it into a bit buffer, and produce bytes as soon as we have >= 8 bits.
        """
        bit_buffer = 0
        bits_in_buffer = 0
        out_bytes = bytearray()

        for ch in tqdm(encoded_str, desc="Decoding", unit="char", unit_scale=True):
            val = self.char_to_value.get(ch)
            if val is None:
                raise ValueError(f"Invalid character '{ch}' in decode.")
            bit_buffer = (bit_buffer << self.chunk_bits) | val
            bits_in_buffer += self.chunk_bits

            # Produce full bytes while possible
            while bits_in_buffer >= 8:
                bits_in_buffer -= 8
                byte_val = (bit_buffer >> bits_in_buffer) & 0xFF
                out_bytes.append(byte_val)

        # If there's leftover bits, interpret them as a final partial byte
        if bits_in_buffer > 0:
            # e.g., if 4 bits left, that's a nibble => 0..15
            byte_val = bit_buffer & ((1 << bits_in_buffer) - 1)
            out_bytes.append(byte_val)

        return bytes(out_bytes)

    # -------------------------------------------------------------------------
    # 3) Encode File -> Filenames
    # -------------------------------------------------------------------------
    def encode_file_to_filenames(self, input_file: str, base_output_dir: str) -> None:
        """
        Read & compress a file, streaming-encode it to a big string,
        then split that string into filenames of length <= chunk_size.

        The result is a directory structure:
            base_output_dir/
                <fileName_extension>/
                    part_00001/
                        000_<chunk>
                        001_<chunk>
                        ...
                    part_00002/
                        ...
        """
        base_name = os.path.basename(input_file)
        name, ext = os.path.splitext(base_name)
        # e.g., "video", ".mp4"
        # We'll store them as "video_mp4" for the folder
        modified_name = f"{name}_{ext.lstrip('.')}"

        main_folder = os.path.join(base_output_dir, modified_name)
        os.makedirs(main_folder, exist_ok=True)

        # Read file, compress, then streaming-encode
        with open(input_file, "rb") as f:
            original_data = f.read()
        logger.info(f"Read {len(original_data)} bytes from '{input_file}'.")

        compressed_data = zlib.compress(original_data, level=9)
        logger.info(f"Compressed to {len(compressed_data)} bytes.")

        encoded_str = self._encode_streaming(compressed_data)
        logger.info(f"Final encoded length: {len(encoded_str)} characters.")

        # Split into chunked filenames
        chunks = [
            encoded_str[i : i + self.chunk_size]
            for i in range(0, len(encoded_str), self.chunk_size)
        ]
        total_chunks = len(chunks)

        current_part_index = 0
        file_count_in_part = 0

        for i, chunk_data in enumerate(chunks):
            if i % self.max_files_per_part == 0:
                current_part_index += 1
                file_count_in_part = 0
                part_folder_path = os.path.join(
                    main_folder,
                    f"part_{current_part_index:05d}"
                )
                os.makedirs(part_folder_path, exist_ok=True)
                logger.debug(f"Created folder: {part_folder_path}")

            filename = f"{file_count_in_part:03d}_{chunk_data}"
            filepath = os.path.join(main_folder, f"part_{current_part_index:05d}", filename)

            # Create empty file
            with open(filepath, "wb"):
                pass

            file_count_in_part += 1

        logger.info(
            f"Created {total_chunks} chunk files in '{main_folder}' "
            f"across {current_part_index} part folder(s)."
        )

    # -------------------------------------------------------------------------
    # 4) Decode Filenames -> File
    # -------------------------------------------------------------------------
    def decode_filenames_to_file(self, main_folder: str, output_file: str) -> None:
        """
        Gather zero-byte files from the structure created by encode_file_to_filenames,
        reconstruct the big encoded string, streaming-decode it,
        and finally decompress to get the original file data.
        """
        all_entries: List[Tuple[int, int, str]] = []

        # Find subfolders named "part_00001", "part_00002", ...
        for entry in os.scandir(main_folder):
            if entry.is_dir() and entry.name.startswith("part_"):
                part_str = entry.name[5:]  # e.g. "00001"
                try:
                    pidx = int(part_str)
                except ValueError:
                    continue

                for f in os.scandir(entry.path):
                    if f.is_file():
                        parts = f.name.split('_', 1)
                        if len(parts) == 2:
                            file_idx_str, chunk_data = parts
                            try:
                                fidx = int(file_idx_str)
                                all_entries.append((pidx, fidx, chunk_data))
                            except ValueError:
                                pass

        # Sort by part idx, then file idx
        all_entries.sort()

        if not all_entries:
            raise ValueError(f"No valid chunk files found under '{main_folder}'.")

        # Reassemble into one long encoded string
        bigbase_str = "".join(chunk_data for _, _, chunk_data in all_entries)

        logger.info(
            f"Reassembled {len(all_entries)} chunks into an encoded string of length {len(bigbase_str)}."
        )

        # Streaming decode, then decompress
        compressed_data = self._decode_streaming(bigbase_str)
        original_data = zlib.decompress(compressed_data)

        # Write output
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "wb") as out_f:
            out_f.write(original_data)

        logger.info(f"Decoded and wrote {len(original_data)} bytes into '{output_file}'.")
