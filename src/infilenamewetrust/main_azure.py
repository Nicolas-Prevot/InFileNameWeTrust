import os
import argparse
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

from .encoder import InFileNameEncoder
from .azure_storage import AzureBlobStorageHandler


def azure_encode() -> None:
    """
    Encode a file into zero-byte Azure blobs.
    """
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Store entire file contents in blob names by encoding a file into chunked blob names."
    )
    parser.add_argument("input_file", help="Path to the local input file.")
    parser.add_argument("container_name", help="Name of the Azure Blob container.")
    parser.add_argument("blob_prefix", help="Blob 'folder' or prefix where the chunks will be stored.")
    parser.add_argument("--chunk_size", type=int, default=3650, help="Max BMP characters per chunk (default: 3650).")
    parser.add_argument("--segment_size", type=int, default=6_200_000, help="Compressed segment size in bytes (default: 6200000).")
    args = parser.parse_args()

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv("AZURE_CONNECTION_STRING"))
    container_client = blob_service_client.get_container_client(args.container_name)

    storage_handler = AzureBlobStorageHandler(container_client, args.blob_prefix)
    encoder = InFileNameEncoder(segment_size=args.segment_size, chunk_size=args.chunk_size)
    encoder.encode_file(args.input_file, storage_handler)


def azure_decode() -> None:
    """
    Decode blob names back into the original file.
    """
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Decode blob names to reconstruct the original file."
    )
    parser.add_argument("container_name", help="Name of the Azure Blob container.")
    parser.add_argument("blob_prefix", help="Blob 'folder' or prefix where the chunks are stored.")
    parser.add_argument("output_file", help="Path to write the decoded file locally.")
    args = parser.parse_args()

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv("AZURE_CONNECTION_STRING"))
    container_client = blob_service_client.get_container_client(args.container_name)

    storage_handler = AzureBlobStorageHandler(container_client, args.blob_prefix)
    encoder = InFileNameEncoder()  # Using default parameters
    encoder.decode_file(storage_handler, args.output_file)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Please specify a command: encode or decode.")
    else:
        cmd = sys.argv[0].split(os.sep)[-1]
        if "encode" in cmd:
            azure_encode()
        elif "decode" in cmd:
            azure_decode()