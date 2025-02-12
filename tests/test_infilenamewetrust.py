"""
Pytest for InFileNameWeTrust encode/decode round-trip.
"""

import os
import tempfile
import zlib

import pytest
from infilenamewetrust.handler import InFileNameStorageCython

@pytest.fixture
def sample_data() -> bytes:
    """Generate some sample binary data."""
    return b"The quick brown fox jumps over the lazy dog" * 100

@pytest.fixture
def empty_data() -> bytes:
    """Generate empty data."""
    return b""

@pytest.fixture
def storage() -> InFileNameStorageCython:
    """Return a configured instance of the storage manager."""
    return InFileNameStorageCython(segment_size=300, chunk_size=100)

def test_encode_decode_round_trip(tmp_path, sample_data, storage):
    """Test that data can be compressed, encoded, decoded, and decompressed properly."""
    input_file = tmp_path / "input.bin"
    output_file = tmp_path / "output.bin"
    input_file.write_bytes(sample_data)

    encoded_dir = tmp_path / "encoded"
    storage.encode_file_to_filenames(str(input_file), str(encoded_dir))
    storage.decode_filenames_to_file(str(encoded_dir), str(output_file))
    output_data = output_file.read_bytes()
    assert output_data == sample_data, "Decoded data does not match original."

def test_empty_file(tmp_path, empty_data, storage):
    """Test encoding/decoding for an empty file."""
    input_file = tmp_path / "empty.bin"
    output_file = tmp_path / "empty_out.bin"
    input_file.write_bytes(empty_data)

    encoded_dir = tmp_path / "empty_encoded"
    storage.encode_file_to_filenames(str(input_file), str(encoded_dir))
    storage.decode_filenames_to_file(str(encoded_dir), str(output_file))
    output_data = output_file.read_bytes()
    assert output_data == empty_data, "Decoded empty file does not match original."

def test_corrupted_segment(tmp_path, sample_data, storage):
    """Test that decoding fails or handles a corrupted segment gracefully."""
    input_file = tmp_path / "input.bin"
    output_file = tmp_path / "output.bin"
    input_file.write_bytes(sample_data)

    encoded_dir = tmp_path / "encoded"
    storage.encode_file_to_filenames(str(input_file), str(encoded_dir))

    # Simulate corruption: remove one part folder (if more than one exists).
    part_folders = [entry for entry in os.scandir(str(encoded_dir)) if entry.is_dir()]
    if part_folders:
        corrupted_part = part_folders[0].path
        # Remove the corrupted part folder.
        import shutil
        shutil.rmtree(corrupted_part)

    with pytest.raises(Exception):
        storage.decode_filenames_to_file(str(encoded_dir), str(output_file))
