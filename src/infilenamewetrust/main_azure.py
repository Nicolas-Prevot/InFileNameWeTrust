import os
import argparse
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

from infilenamewetrust.handler import InFileNameStorageCython


def azure_encode() -> None:
    """
    Encode a file into zero-byte Azure blobs (blob names store the data).
    """
    load_dotenv()
    parser = argparse.ArgumentParser(
        description=(
            "Store entire file contents in blob names by encoding a file into chunked blob names."
        )
    )
    parser.add_argument("input_file", help="Path to the local input file.")
    parser.add_argument("container_name", help="Name of the Azure Blob container.")
    parser.add_argument("blob_prefix", help="Blob 'folder' or prefix where the chunks will be stored.")
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=3650,
        help="Max BMP characters per chunk (default: 3650).",
    )
    parser.add_argument(
        "--segment_size",
        type=int,
        default=6_200_000,
        help="Compressed segment size in bytes (default: 6_200_000).",
    )
    args = parser.parse_args()

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv("AZURE_CONNECTION_STRING"))
    container_client = blob_service_client.get_container_client(args.container_name)

    storage = InFileNameStorageCython(
        chunk_size=args.chunk_size,
        segment_size=args.segment_size
    )

    storage.encode_file_to_azure_blobs(
        input_file=args.input_file,
        container_client=container_client,
        blob_prefix=args.blob_prefix
    )


def azure_decode() -> None:
    """
    Decode chunked blob names back into the original file (download).
    """
    load_dotenv()
    parser = argparse.ArgumentParser(
        description=(
            "Decode blob names that store an original file (zero-byte blobs whose names encode the data)."
        )
    )
    parser.add_argument("container_name", help="Name of the Azure Blob container.")
    parser.add_argument("blob_prefix", help="Blob 'folder' or prefix where the chunks are stored.")
    parser.add_argument("output_file", help="Path to write the decoded file locally.")
    args = parser.parse_args()

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv("AZURE_CONNECTION_STRING"))
    container_client = blob_service_client.get_container_client(args.container_name)

    storage = InFileNameStorageCython()  # default chunk_size + segment_size
    storage.decode_azure_blobs_to_file(
        container_client=container_client,
        blob_prefix=args.blob_prefix,
        output_file=args.output_file
    )


if __name__ == "__main__":
    # Dispatch based on the invoked script name
    import sys
    if len(sys.argv) < 2:
        print("Please specify a command: encode, decode")
    else:
        cmd = sys.argv[0].split(os.sep)[-1]
        if "encode" in cmd:
            azure_encode()
        elif "decode" in cmd:
            azure_decode()