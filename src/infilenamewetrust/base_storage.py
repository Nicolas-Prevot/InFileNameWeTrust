from abc import ABC, abstractmethod

class BaseStorageHandler(ABC):
    @abstractmethod
    def store_segment(self, seg_index: int, encoded_segment: str, chunk_size: int) -> None:
        """
        Store one encoded segment.
        """
        pass

    @abstractmethod
    def retrieve_segments(self) -> dict:
        """
        Retrieve stored encoded segments.
        Returns:
            dict: Mapping of segment index (int) to encoded segment (str).
        """
        pass