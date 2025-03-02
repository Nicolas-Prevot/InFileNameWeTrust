"""
Module for file encoding/decoding logic independent of storage specifics.
"""

import os
import zlib
from loguru import logger
from tqdm import tqdm

from .cython_fastencode import encode as cy_encode, decode as cy_decode
from .utils import build_bmp_singleunit_alphabet


class InFileNameEncoder:
    """
    Handles file transformation: compression, segmentation, encoding, and decoding.
    """

    def __init__(self, segment_size: int = 100_000, chunk_size: int = 240) -> None:
        self.segment_size = segment_size
        self.chunk_size = chunk_size
        self.alphabet = build_bmp_singleunit_alphabet()
        self.base_size = len(self.alphabet)
        # Determine chunk_bits = largest n such that 2^n <= base_size
        self.chunk_bits = 0
        while (1 << self.chunk_bits) <= self.base_size:
            self.chunk_bits += 1
        self.chunk_bits -= 1
        logger.debug(f"chunk_bits = {self.chunk_bits}, base_size = {self.base_size}")
        # Build a reverse map for the first 2^chunk_bits characters
        limit = (1 << self.chunk_bits)
        self.reverse_map = {ch: i for i, ch in enumerate(self.alphabet) if i < limit}
        logger.info(f"Using an alphabet subset of size = {limit} out of {self.base_size}")

    def encode_file(self, input_file: str, storage_handler) -> None:
        """
        Encode a file and delegate storage of encoded segments using the provided storage handler.
        """
        with open(input_file, "rb") as f:
            original_data = f.read()
        logger.info(f"Read {len(original_data)} bytes from '{input_file}'")
        compressed_data = zlib.compress(original_data, level=9)
        logger.info(f"Compressed to {len(compressed_data)} bytes")
        # Segment the compressed data
        segments = []
        start = 0
        comp_len = len(compressed_data)
        while start < comp_len:
            end = min(start + self.segment_size, comp_len)
            segments.append(compressed_data[start:end])
            start = end
        logger.info(f"Divided compressed data into {len(segments)} segments (~{self.segment_size} bytes each).")

        for seg_index, seg in enumerate(tqdm(segments, desc="Encoding segments"), start=1):
            seg_len = len(seg)
            header = seg_len.to_bytes(4, byteorder="big")
            seg_with_header = header + seg
            encoded = cy_encode(seg_with_header, self.chunk_bits, self.alphabet)
            # Delegate storage to the provided storage handler
            storage_handler.store_segment(seg_index, encoded, self.chunk_size)
            logger.info(f"Segment {seg_index} encoded into {len(encoded)} characters.")

    def decode_file(self, storage_handler, output_file: str) -> None:
        """
        Retrieve encoded segments using the storage handler, decode, and reconstruct the original file.
        """
        segments = storage_handler.retrieve_segments()
        if not segments:
            raise ValueError("No segments retrieved from storage.")
        # Process segments in order of segment index
        accumulated_compressed = bytearray()
        for seg_index in sorted(segments.keys()):
            encoded = segments[seg_index]
            dec_data = cy_decode(encoded, self.chunk_bits, self.reverse_map)
            if len(dec_data) < 4:
                logger.error(f"Segment {seg_index}: decoded data is too short to contain a header.")
                continue
            expected_seg_len = int.from_bytes(dec_data[:4], byteorder="big")
            seg_data = dec_data[4:4+expected_seg_len]
            if len(seg_data) != expected_seg_len:
                logger.warning(f"Segment {seg_index}: expected {expected_seg_len} bytes, got {len(seg_data)} bytes.")
            accumulated_compressed.extend(seg_data)
            logger.info(f"Segment {seg_index}: header indicated {expected_seg_len} bytes, decoded {len(seg_data)} bytes.")
        original_data = zlib.decompress(accumulated_compressed)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "wb") as f:
            f.write(original_data)
        logger.info(f"Decoded file written: {output_file}")