import argparse
from infilenamewetrust.storage import InFileNameStorage

def encode():
    parser = argparse.ArgumentParser(
        description="Store entire file contents in zero-byte filenames! Encode a file into chunked filenames."
    )

    parser.add_argument("input_file", help="Path to the input file.")
    parser.add_argument("output_dir", help="Directory for the chunk files.")
    parser.add_argument("--chunk_size", type=int, default=190,
                        help="Max BMP characters per chunk (default=200).")
    
    args = parser.parse_args()

    storage = InFileNameStorage(chunk_size=args.chunk_size)
    storage.encode_file_to_filenames(args.input_file, args.output_dir)

def decode():
    parser = argparse.ArgumentParser(
        description="Store entire file contents in zero-byte filenames! Decode chunked files back into the original file."
    )
    parser.add_argument("input_dir", help="Directory containing chunk files.")
    parser.add_argument("output_file", help="Path to write decoded file.")

    args = parser.parse_args()
    storage = InFileNameStorage()
    storage.decode_filenames_to_file_v2(args.input_dir, args.output_file)