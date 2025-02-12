"""
Main entry point for InFileNameWeTrust.

Provides command-line interfaces for encoding and decoding files.
"""

import os
import argparse
from infilenamewetrust.handler import InFileNameStorageCython

def encode() -> None:
    """
    Encode a file into chunked filenames.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Store entire file contents in zero-byte filenames by encoding a file into chunked filenames."
        )
    )
    parser.add_argument("input_file", help="Path to the input file.")
    parser.add_argument("output_dir", help="Directory where the chunk files will be created.")
    parser.add_argument("--chunk_size", type=int, default=190,
                        help="Max BMP characters per chunk (default: 190).")
    parser.add_argument("--segment_size", type=int, default=300_000,
                        help="Compressed segment size in bytes (default: 300000).")
    args = parser.parse_args()

    storage = InFileNameStorageCython(chunk_size=args.chunk_size, segment_size=args.segment_size)
    storage.encode_file_to_filenames(args.input_file, args.output_dir)

def decode() -> None:
    """
    Decode chunked filenames back into the original file.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Decode chunked filenames to reconstruct the original file."
        )
    )
    parser.add_argument("input_dir", help="Directory containing the chunk files.")
    parser.add_argument("output_file", help="Path to write the decoded file.")
    args = parser.parse_args()

    storage = InFileNameStorageCython()
    storage.decode_filenames_to_file(args.input_dir, args.output_file)


def test() -> None:
    """
    Run a test encoding and decoding round-trip.
    """
    parser = argparse.ArgumentParser(
        description="Test round-trip encode and decode."
    )
    parser.add_argument("input_file", help="Path to the file to test.")
    parser.add_argument("output_file", help="Path to write the decoded file.")
    args = parser.parse_args()

    storage = InFileNameStorageCython(chunk_size=190, segment_size=300_000)
    storage.test_encode_decode(args.input_file, args.output_file)

if __name__ == "__main__":
    # Dispatch based on the invoked script name
    import sys
    if len(sys.argv) < 2:
        print("Please specify a command: encode, decode, or test.")
    else:
        cmd = sys.argv[0].split(os.sep)[-1]
        if "encode" in cmd:
            encode()
        elif "decode" in cmd:
            decode()
        elif "test" in cmd:
            test()