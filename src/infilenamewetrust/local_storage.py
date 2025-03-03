import os
from loguru import logger

from .base_storage import BaseStorageHandler


class LocalStorageHandler(BaseStorageHandler):
    def __init__(self, base_output_dir: str):
        self.base_output_dir = base_output_dir

    def store_segment(self, seg_index: int, encoded_segment: str, chunk_size: int) -> None:
        part_folder = os.path.join(self.base_output_dir, f"part_{seg_index:05d}")
        os.makedirs(part_folder, exist_ok=True)
        # Split the encoded segment into chunks
        for idx, i in enumerate(range(0, len(encoded_segment), chunk_size)):
            chunk = encoded_segment[i:i+chunk_size]
            filename = f"{idx:03d}_{chunk}"
            filepath = os.path.join(part_folder, filename)
            with open(filepath, "wb") as f:
                pass  # Create a zero-byte file with the name encoding the chunk
        logger.info(f"Stored segment {seg_index} in {part_folder}")

    def retrieve_segments(self) -> dict:
        segments = {}
        # Each segment is stored in a folder named "part_{seg_index:05d}"
        for entry in os.scandir(self.base_output_dir):
            if entry.is_dir() and entry.name.startswith("part_"):
                try:
                    seg_index = int(entry.name[5:])
                except ValueError:
                    continue
                chunk_files = []
                # For each file in the folder, extract the chunk data after the underscore
                for file_entry in os.scandir(entry.path):
                    if file_entry.is_file():
                        # Filename format: "XXX_<chunk>"
                        parts = file_entry.name.split("_", 1)
                        if len(parts) == 2:
                            try:
                                idx = int(parts[0])
                            except ValueError:
                                continue
                            chunk_files.append((idx, parts[1]))
                # Sort by chunk index and reassemble the encoded segment string
                chunk_files.sort(key=lambda x: x[0])
                encoded_segment = "".join(chunk for idx, chunk in chunk_files)
                segments[seg_index] = encoded_segment
        return segments