# InFileNameWeTrust

**InFileNameWeTrust** is a whimsical experiment that stores entire file contents in the filenames themselves—the ultimate proof-of-concept for “hidden” storage via filename abuse on Windows.

Each file is **0 bytes**, yet it secretly embeds all your data in its name. It’s silly, it’s impractical, but it works—and that’s precisely why we love it.

No disclaimers—just pure madness. InFileNameWeTrust!

## How It Works

1. **Compression**  
   The input file is compressed with zlib.

2. **Base‑N Encoding**  
   The compressed bytes are interpreted as a large integer and converted into a high‑base representation. The “digits” are valid Unicode BMP characters allowed in Windows filenames.

3. **Chunking**  
   Since Windows limits filename length (usually 255 UTF‑16 code units), the encoded string is split into chunks small enough to serve as filenames. Each chunk becomes a **zero‑byte file** whose name encodes part of your data.

4. **Decoding**  
    - The filenames are sorted by their numeric prefix.
    - The encoded chunks are concatenated.
    - The data is decoded from base‑N back to bytes.
    - zlib decompression restores the original file.

## Installation and Usage

1. **Clone the Repository**

    ```bash
    git clone https://github.com/Nicolas-Prevot/InFileNameWeTrust.git
    cd InFileNameWeTrust
    ```

2. **Create the Environment**

    If you use Conda:

    ```bash
    conda env create -f environment.yml
    conda activate infilenamewetrust
    ```

3. **Install with Poetry**

    ```bash
    poetry install
    ```

### Encoding

```bash
poetry run encode /path/to/input_file /path/to/output_dir
```

- **input_file**: The file you want to store in filenames.
- **output_dir**: The directory to create the “chunk files.”
- **Options**:
  - `--chunk_size <N>`: Max BMP characters per chunk (default=240).
  - `--segment_size <N>`: Compressed segment size in bytes (default: 300000).

### Decoding

```bash
poetry run decode /path/to/output_dir /path/to/restored_file
```

- **input_dir**: The directory containing the chunk files.
- **output_file**: Where to write the reconstructed data.

### Example

```bash
poetry run encode README.md ./data
poetry run decode ./data/README_md ./data/README.md
```

## Azure usage

```bash
poetry run azure_encode /path/to/input_file container_name blob_prefix --chunk_size 3650 --segment_size 6_200_000
```

```bash
poetry run azure_decode container_name blob_prefix /path/to/restored_file
```

```bash
poetry run azure_encode "C:/Users/Utilisateur/Downloads/image.png" "test1" "data/image_0"
poetry run azure_decode "test1" "data/image_0" "./data/image_0.png"
```

### Running Tests

The repository includes pytest tests. To run the tests, execute:

```bash
poetry run pytest
```

### Build the Cython Module (Optional)

From within `src/infilenamewetrust`, you can build the Cython extension with:

```bash
python setup.py build_ext --inplace
```

## Fancy Ideas to Explore

- **Alternate Data Streams (ADS)**: Hide data in `filename:stream` to store “secret” streams.
- **Timestamps**: Encode small blocks of data in the creation/mod/access times.
Short (8.3) Names: If 8.3 short-name generation is enabled, store data in the DOS short name.
- **Folder Names / ACLs / Reparse Points**: Exploit other NTFS features as “containers” for data.
- **Registry Keys**: Similar concept, but storing chunked data in registry subkeys or value names.
