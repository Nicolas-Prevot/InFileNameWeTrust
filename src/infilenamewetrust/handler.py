"""
Handler module for InFileNameWeTrust.

This module compresses, segments, encodes, and decodes files by storing data in filenames.
"""

import os
import zlib
from typing import List, Tuple
from loguru import logger

from infilenamewetrust import cython_fastencode


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


class InFileNameStorageCython:
    """
    Manager class that:
      - Compresses data.
      - Splits it into segments.
      - Encodes each segment via Cython.
      - Stores the data in chunked filenames.
    """

    def __init__(self, segment_size: int = 100_000, chunk_size: int = 240) -> None:
        """
        Initialize the storage manager.

        Parameters
        ----------
        segment_size : int, optional
            Maximum size (in bytes) of each compressed segment, by default 100000.
        chunk_size : int, optional
            Maximum length (in characters) of each filename chunk, by default 240.
        """
        self.segment_size = segment_size
        self.chunk_size = chunk_size

        self.alphabet = build_bmp_singleunit_alphabet()
        self.base_size = len(self.alphabet)

        # Determine chunk_bits = largest n so that 2^n <= base_size
        self.chunk_bits = 0
        while (1 << self.chunk_bits) <= self.base_size:
            self.chunk_bits += 1
        self.chunk_bits -= 1
        logger.debug(f"chunk_bits = {self.chunk_bits}, base_size={self.base_size}")

        # Build a reverse map only for the first 2^chunk_bits
        limit = (1 << self.chunk_bits)
        self.reverse_map = {}
        for i, ch in enumerate(self.alphabet):
            if i < limit:
                self.reverse_map[ch] = i
        logger.info(f"Using an alphabet subset of size = {limit} out of {self.base_size}")

    def test_encode_decode(self, input_file: str, output_file: str) -> None:
        """
        Test round-trip encoding/decoding on a given file.

        Parameters
        ----------
        input_file : str
            Path to the file to test.
        output_file : str
            Path where the decoded file will be written.
        """
        with open(input_file, "rb") as f:
            original_data: bytes = f.read()
        logger.info(f"Read {len(original_data)} bytes from '{input_file}'")
        compressed_data: bytes = zlib.compress(original_data, level=9)
        logger.info(f"Compressed to {len(compressed_data)} bytes")
        compressed_len: int = len(compressed_data)

        encoded: str = cython_fastencode.encode(compressed_data, self.chunk_bits, self.alphabet)
        logger.info(f"Encoded length: {len(encoded)} characters")
        decoded: bytes = cython_fastencode.decode(encoded, self.chunk_bits, self.reverse_map)
        logger.info(f"Decoded length: {len(decoded)} bytes")
        # Trim any padded bytes.
        decoded = decoded[:compressed_len]
        original_data = zlib.decompress(decoded)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "wb") as f:
            f.write(original_data)
        logger.info(f"Decoded => wrote {len(original_data)} bytes to '{output_file}'")


    def encode_file_to_filenames(self, input_file: str, base_output_dir: str) -> None:
        """
        Compress and encode a file, splitting the encoded data into filename chunks.

        Each segment is prefixed with a 4-byte header that stores its original length.

        Parameters
        ----------
        input_file : str
            Path to the input file.
        base_output_dir : str
            Base directory where the filename chunks will be created.
        """
        base_name = os.path.basename(input_file)
        name, ext = os.path.splitext(base_name)
        folder_name = f"{name}_{ext.lstrip('.')}"  # e.g. "video_mp4"
    
        main_folder = os.path.join(base_output_dir, folder_name)
        os.makedirs(main_folder, exist_ok=True)
    
        # Read & compress the file
        with open(input_file, "rb") as f:
            original_data = f.read()
        logger.info(f"Read {len(original_data)} bytes from '{input_file}'")
    
        compressed_data = zlib.compress(original_data, level=9)
        logger.info(f"Compressed to {len(compressed_data)} bytes")
    
        # Segment the compressed data into pieces of at most self.segment_size bytes.
        segments: List[bytes] = []
        start = 0
        comp_len = len(compressed_data)
        while start < comp_len:
            end = min(start + self.segment_size, comp_len)
            segment = compressed_data[start:end]
            segments.append(segment)
            start = end
        logger.info(f"Divided compressed data into {len(segments)} segments (~{self.segment_size} bytes each).")
    
        # Process each segment.
        seg_index = 0
        for seg in segments:
            seg_index += 1
            seg_len = len(seg)
            # Create a 4-byte header to store the length of the original segment.
            # (4 bytes is enough for segments up to 4GB.)
            header = seg_len.to_bytes(4, byteorder="big")
            seg_with_header = header + seg
    
            # Encode the header+segment.
            encoded = cython_fastencode.encode(seg_with_header, self.chunk_bits, self.alphabet)
    
            # Create a folder for this segment (e.g. "part_00001").
            part_folder = os.path.join(main_folder, f"part_{seg_index:05d}")
            os.makedirs(part_folder, exist_ok=True)
    
            # Split the encoded string into chunks (each chunk becomes a filename).
            chunks = [
                encoded[i : i + self.chunk_size]
                for i in range(0, len(encoded), self.chunk_size)
            ]
            file_idx_in_part = 0
            for chunk_data in chunks:
                # Build the filename: use a numeric prefix then the chunk data.
                filename = f"{file_idx_in_part:03d}_{chunk_data}"
                filepath = os.path.join(part_folder, filename)
                # Create an empty file; the file's name encodes the data.
                with open(filepath, "wb"):
                    pass
                file_idx_in_part += 1
    
            logger.info(f"Segment {seg_index} => Encoded length={len(encoded)}, wrote {len(chunks)} filenames.")

    def decode_filenames_to_file(self, main_folder: str, output_file: str) -> None:
        """
        Reassemble and decode the file data from the encoded filename chunks.

        Parameters
        ----------
        main_folder : str
            The directory containing the part folders.
        output_file : str
            The path to write the decoded (original) file.
        """
        # Find all part folders (e.g. "part_00001", "part_00002", etc.)
        part_folders: List[Tuple[int, str]] = []
        for entry in os.scandir(main_folder):
            if entry.is_dir() and entry.name.startswith("part_"):
                idx_str = entry.name[5:]
                try:
                    idx = int(idx_str)
                    part_folders.append((idx, entry.path))
                except ValueError:
                    pass
        part_folders.sort(key=lambda x: x[0])
        if not part_folders:
            raise ValueError(f"No part_XXXXX folders in '{main_folder}'")
    
        accumulated_compressed = bytearray()
        seg_index = 0
    
        # Process each segment folder in order.
        for part_idx, part_path in part_folders:
            seg_index += 1
            # Gather the chunk files in this folder. Each file's name is of the form "NNN_<chunk>".
            file_entries: List[Tuple[int, str]] = []
            for fentry in os.scandir(part_path):
                if fentry.is_file():
                    splitted = fentry.name.split("_", 1)
                    if len(splitted) == 2:
                        try:
                            fidx = int(splitted[0])
                            chunk_data = splitted[1]
                            file_entries.append((fidx, chunk_data))
                        except ValueError:
                            pass
            file_entries.sort(key=lambda x: x[0])
            if not file_entries:
                logger.warning(f"No chunk files in {part_path}. Skipping this segment.")
                continue
    
            # Reassemble the encoded string for this segment.
            segment_str = "".join(chunk for _, chunk in file_entries)
    
            # Decode the segment (this returns header + original segment + possible padding).
            dec_data = cython_fastencode.decode(segment_str, self.chunk_bits, self.reverse_map)
    
            if len(dec_data) < 4:
                logger.error(f"Segment {seg_index}: decoded data is too short to contain a header.")
                continue
    
            # Read the first 4 bytes as the header containing the segment length.
            expected_seg_len = int.from_bytes(dec_data[:4], byteorder="big")
            # Extract the segment data and trim any extra padded bytes.
            seg_data = dec_data[4 : 4 + expected_seg_len]
    
            if len(seg_data) != expected_seg_len:
                logger.warning(
                    f"Segment {seg_index}: expected {expected_seg_len} bytes, got {len(seg_data)} bytes after trimming."
                )
    
            accumulated_compressed.extend(seg_data)
            logger.info(f"Segment {seg_index}: header indicated {expected_seg_len} bytes, decoded {len(seg_data)} bytes.")
    
        logger.info(f"Reassembled {seg_index} segments; total accumulated compressed size = {len(accumulated_compressed)} bytes.")
    
        # Decompress the reassembled compressed data.
        original_data = zlib.decompress(accumulated_compressed)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "wb") as f:
            f.write(original_data)
        logger.info(f"Decoded => wrote {len(original_data)} bytes to '{output_file}'.")
