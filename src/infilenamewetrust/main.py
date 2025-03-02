"""
Main entry point for local encoding/decoding using the file system.
"""

import os
import argparse

from .encoder import InFileNameEncoder
from .local_storage import LocalStorageHandler


def encode() -> None:
    """
    Encode a file into chunked filenames on the local file system.
    """
    parser = argparse.ArgumentParser(
        description="Store entire file contents in zero-byte filenames by encoding a file into chunked filenames."
    )
    parser.add_argument("input_file", help="Path to the input file.")
    parser.add_argument("output_dir", help="Directory where the chunk files will be created.")
    parser.add_argument("--chunk_size", type=int, default=190, help="Max BMP characters per chunk (default: 190).")
    parser.add_argument("--segment_size", type=int, default=300_000, help="Compressed segment size in bytes (default: 300000).")
    args = parser.parse_args()

    storage_handler = LocalStorageHandler(args.output_dir)
    encoder = InFileNameEncoder(segment_size=args.segment_size, chunk_size=args.chunk_size)
    encoder.encode_file(args.input_file, storage_handler)


def decode() -> None:
    """
    Decode chunked filenames on the local file system back into the original file.
    """
    parser = argparse.ArgumentParser(
        description="Decode chunked filenames to reconstruct the original file."
    )
    parser.add_argument("input_dir", help="Directory containing the chunk files.")
    parser.add_argument("output_file", help="Path to write the decoded file.")
    args = parser.parse_args()

    storage_handler = LocalStorageHandler(args.input_dir)
    encoder = InFileNameEncoder()
    encoder.decode_file(storage_handler, args.output_file)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Please specify a command: encode, decode")
    else:
        cmd = sys.argv[0].split(os.sep)[-1]
        if "encode" in cmd:
            encode()
        elif "decode" in cmd:
            decode()
