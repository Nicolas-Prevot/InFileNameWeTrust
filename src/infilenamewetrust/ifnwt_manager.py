import os
import zlib
import math
import argparse
from typing import List, Tuple
from loguru import logger

# Import our compiled Cython extension
import cython_fastencode

################################################################################
# 1) Build BMP Alphabet
################################################################################

def is_valid_bmp_char(cp: int) -> bool:
    """Check if a codepoint is a valid single-code-unit BMP char for Windows filenames."""
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
    chars = []
    for cp in range(0x10000):
        if is_valid_bmp_char(cp):
            chars.append(chr(cp))
    return "".join(chars)


################################################################################
# 2) The Manager Class
################################################################################

class InFileNameStorageCython:
    """
    Manager that:
    - compresses data
    - splits it into ~100kB segments
    - encodes each segment via Cython
    - stores them in chunked filenames
    """

    def __init__(self, 
                 segment_size=100_000,   # each compressed segment
                 chunk_size=240,        # each filename length
                 max_files_per_part=1000):
        self.segment_size = segment_size
        self.chunk_size = chunk_size
        print(chunk_size)
        self.max_files_per_part = max_files_per_part

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

    def encode_file_to_filenames(self, input_file: str, base_output_dir: str):
        """
        Steps:
        1) read & compress
        2) segment the compressed data in ~ self.segment_size
        3) encode each segment with cython_fastencode.encode_chunk_py
        4) store each encoded segment as a series of chunked filenames
        """

        base_name = os.path.basename(input_file)
        name, ext = os.path.splitext(base_name)
        folder_name = f"{name}_{ext.lstrip('.')}"  # e.g. "video_mp4"

        main_folder = os.path.join(base_output_dir, folder_name)
        os.makedirs(main_folder, exist_ok=True)

        # Read & compress
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
            segment = compressed_data[start:end]
            segments.append(segment)
            start = end
        logger.info(f"Divided compressed data into {len(segments)} segments of ~{self.segment_size} bytes each.")

        # Encode each segment -> store as chunked filenames
        seg_index = 0
        for seg in segments:
            seg_index += 1
            # encode with Cython
            encoded = cython_fastencode.encode_chunk_py(seg, self.chunk_bits, self.alphabet)
            # store in "part_SSSSS_<segIndex> folder? or reuse the same approach you had
            part_folder = os.path.join(main_folder, f"part_{seg_index:05d}")
            os.makedirs(part_folder, exist_ok=True)

            # Now chunk that 'encoded' string
            chunks = [
                encoded[i : i + self.chunk_size]
                for i in range(0, len(encoded), self.chunk_size)
            ]
            # For each chunk, we name the file "000_<chunk>" etc.
            file_idx_in_part = 0
            for i, chunk_data in enumerate(chunks):
                filename = f"{file_idx_in_part:03d}_{chunk_data}"
                filepath = os.path.join(part_folder, filename)
                with open(filepath, "wb"):
                    pass
                file_idx_in_part += 1

            logger.info(f"Segment {seg_index} => Encoded length {len(encoded)} => wrote {len(chunks)} filenames.")

    def decode_filenames_to_file(self, main_folder: str, output_file: str):
        """
        Reverse:
        1) gather subfolders part_00001, part_00002, ...
        2) for each subfolder, gather filenames, reassemble => one encoded string => decode it
        3) accumulate each decoded segment into final compressed data
        4) zlib.decompress => original data
        """
        # subfolders = sorted by numeric index
        part_folders = []
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

        # We'll gather all decoded segments in memory, then combine, then decompress
        # (Alternatively, you could stream it out to a file.)
        accumulated_compressed = bytearray()

        seg_count = 0
        for part_idx, part_path in part_folders:
            seg_count += 1
            # gather chunk files: "000_<chunk>", "001_<chunk>", ...
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
                logger.warning(f"No chunk files in {part_path}. Skipping.")
                continue

            # Reassemble the encoded string for this segment
            segment_str = "".join(cd for _, cd in file_entries)
            # decode with Cython
            dec_segment = cython_fastencode.decode_chunk_py(segment_str, self.chunk_bits, self.reverse_map)
            accumulated_compressed.extend(dec_segment)

        logger.info(f"Reassembled {seg_count} segments, total compressed size {len(accumulated_compressed)} bytes.")

        # Now decompress
        original_data = zlib.decompress(accumulated_compressed)

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "wb") as f:
            f.write(original_data)
        logger.info(f"Decoded => wrote {len(original_data)} bytes to '{output_file}'.")


################################################################################
# 3) Command-Line Interface
################################################################################

def main():
    parser = argparse.ArgumentParser(description="Encode/Decode using chunk-based Cython approach.")
    sub = parser.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encode", help="Encode a file into chunked filenames.")
    enc.add_argument("input_file", help="Path to the input file.")
    enc.add_argument("output_dir", help="Directory for the chunk files.")
    enc.add_argument("--segment_size", type=int, default=100_000,
                     help="Compressed segment size (default=100000).")
    enc.add_argument("--chunk_size", type=int, default=240,
                     help="Max filename length for chunk (default=240).")
    enc.add_argument("--max_files_per_part", type=int, default=1000,
                     help="Max files per subfolder (default=1000).")

    dec = sub.add_parser("decode", help="Decode chunked filenames back into the original file.")
    dec.add_argument("input_dir", help="Directory containing chunked subfolders.")
    dec.add_argument("output_file", help="Path to write the decoded file.")

    args = parser.parse_args()

    storage = InFileNameStorageCython(
        segment_size=args.segment_size if hasattr(args, 'segment_size') else 100_000,
        chunk_size=args.chunk_size if hasattr(args, 'chunk_size') else 240,
        max_files_per_part=args.max_files_per_part if hasattr(args, 'max_files_per_part') else 1000
    )

    if args.command == "encode":
        storage.encode_file_to_filenames(args.input_file, args.output_dir)
    elif args.command == "decode":
        storage.decode_filenames_to_file(args.input_dir, args.output_file)

if __name__ == "__main__":
    main()
