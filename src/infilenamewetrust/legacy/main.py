import argparse
from infilenamewetrust.storage import InFileNameStorage

def encode():
    """
    Encode a file into chunked filenames using zero-byte filenames.

    Command-line arguments:
    - input_file (str): Path to the input file.
    - output_dir (str): Directory where chunk files will be stored.
    - --chunk_size (int, optional): Maximum BMP characters per chunk (default: 190).
    """
    parser = argparse.ArgumentParser(
        description=(
            "Store entire file contents in zero-byte filenames! "
            "Encode a file into chunked filenames."
        )
    )
    parser.add_argument("input_file", help="Path to the input file.")
    parser.add_argument("output_dir", help="Directory for the chunk files.")
    parser.add_argument(
        "--chunk_size", type=int, default=190,
        help="Max BMP characters per chunk (default: 190)."
    )
    args = parser.parse_args()

    storage = InFileNameStorage(chunk_size=args.chunk_size)
    storage.encode_file_to_filenames(args.input_file, args.output_dir)

def decode():
    """
    Decode chunked filenames back into the original file.

    Command-line arguments:
    - input_dir (str): Directory containing chunk files.
    - output_file (str): Path to write the decoded file.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Store entire file contents in zero-byte filenames! "
            "Decode chunked files back into the original file."
        )
    )
    parser.add_argument("input_dir", help="Directory containing chunk files.")
    parser.add_argument("output_file", help="Path to write decoded file.")

    args = parser.parse_args()
    storage = InFileNameStorage()
    storage.decode_filenames_to_file(args.input_dir, args.output_file)