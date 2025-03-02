from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_storage import BaseStorageHandler


class AzureBlobStorageHandler(BaseStorageHandler):
    def __init__(self, container_client, blob_prefix: str):
        self.container_client = container_client
        self.blob_prefix = blob_prefix
    
    def store_segment(self, seg_index: int, encoded_segment: str, chunk_size: int, max_workers: int = 16) -> None:
        part_prefix = f"{self.blob_prefix}/part_{seg_index:05d}"
        chunks = [encoded_segment[i:i+chunk_size] for i in range(0, len(encoded_segment), chunk_size)]
        futures = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for idx, chunk in enumerate(chunks):
                blob_name = f"{part_prefix}/{idx:03d}_{chunk}"
                futures.append(executor.submit(self.container_client.upload_blob, name=blob_name, data=b"", overwrite=True))
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error uploading blob: {e}")
                    raise
        logger.info(f"Segment {seg_index} stored in parallel with {len(chunks)} blobs.")

    def retrieve_segments(self) -> dict:
        segments = {}
        all_blobs = self.container_client.list_blobs(name_starts_with=self.blob_prefix)
        # Organize blobs by segment index
        segments_map = {}
        for blob in all_blobs:
            blob_name = blob.name  # e.g., "prefix/part_00001/000_chunkdata"

            if not blob_name.startswith(self.blob_prefix):
                continue
            relative_name = blob_name[len(self.blob_prefix):].lstrip("/")
            if not relative_name.startswith("part_"):
                continue

            seg_folder, _, remainder = relative_name.partition("/")
            if not remainder:
                continue
            try:
                seg_index = int(seg_folder[5:])
            except ValueError:
                logger.warning(f"Skipping blob with unrecognized folder name: {blob_name}")
                continue
            parts = remainder.split("_", 1)
            if len(parts) != 2:
                logger.warning(f"Skipping blob with unrecognized chunk name: {blob_name}")
                continue
            try:
                file_idx = int(parts[0])
            except ValueError:
                logger.warning(f"Skipping blob with unrecognized chunk name: {blob_name}")
                continue
            chunk_data = parts[1]
            segments_map.setdefault(seg_index, []).append((file_idx, chunk_data))
        for seg_index, chunks in segments_map.items():
            chunks.sort(key=lambda x: x[0])
            encoded_segment = "".join(chunk for idx, chunk in chunks)
            segments[seg_index] = encoded_segment
        return segments