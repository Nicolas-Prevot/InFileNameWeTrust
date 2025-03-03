# InFileNameWeTrust

**InFileNameWeTrust** is a whimsical experiment that stores entire file contents in the filenames themselves. This unconventional method is the ultimate proof-of-concept for *"hidden"* storage via filename abuse on Windows.

Each file is **0 bytes**, yet it secretly embeds all your data in its name. It’s silly, it’s impractical, but it works—and that’s precisely why we love it.

No disclaimers, just pure madness. InFileNameWeTrust!

> The project supports both local file system storage and optional integration with Azure Blob Storage.

## How It Works

1. **Compression**  
   The input file is compressed with zlib.

2. **Base‑N Encoding**  
   The compressed bytes are interpreted as a large integer and converted into a high‑base representation using a custom valid Unicode BMP alphabet allowed in Windows filenames.

3. **Chunking**  
   Since Windows limits filename length (usually 255 UTF‑16 code units), the encoded string is split into chunks small enough to serve as filenames. Each chunk becomes a **zero‑byte file** whose name encodes part of your data.

4. **Decoding**  
    - The filenames are sorted by their numeric prefix.
    - The encoded chunks are concatenated.
    - The data is decoded from base‑N back to bytes.
    - zlib decompression restores the original file.

## Installation

### Prerequisites

- Python 3.10 or newer
- [Poetry](https://python-poetry.org/) for dependency management

### Steps

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

4. **Optional: Install Azure Dependencies**
    To enable Azure Blob Storage functionality, install the optional dependencies:

    ```bash
    poetry install --extras "azure"
    ```

## Usage

### Local Storage

#### Encoding

Store a file’s data in zero-byte filenames on the local file system:

```bash
poetry run encode /path/to/input_file /path/to/output_dir --chunk_size 190 --segment_size 300000
```

- **input_file**: The file you want to store in filenames.
- **output_dir**: The directory to create the *"chunk files"*.
- **Options**:
  - `--chunk_size <N>`: Max BMP characters per chunk (default=190).
  - `--segment_size <N>`: Compressed segment size in bytes (default: 300000).

#### Decoding

Reconstruct the original file from the chunked filenames:

```bash
poetry run decode /path/to/output_dir /path/to/restored_file
```

- **input_dir**: The directory containing the chunk files.
- **output_file**: Where to write the reconstructed data.

#### Example

```bash
poetry run encode README.md ./data/README_md
poetry run decode ./data/README_md ./data/README.md
```

### Azure Blob Storage Usage

The project includes support for storing and retrieving encoded segments as Azure blobs.

#### Encoding Azure

```bash
poetry run azure_encode /path/to/input_file container_name blob_prefix --chunk_size 3650 --segment_size 6_200_000
```

- **input_file**: The file you want to store in filenames.
- **container_name**: Name of the Azure Blob container.
- **blob_prefix**: Blob "folder" or prefix to use for storage.
- **Options**:
  - `--chunk_size <N>`: Max BMP characters per chunk (default=3650).
  - `--segment_size <N>`: Compressed segment size in bytes (default: 6200000).

#### Decoding Azure

```bash
poetry run azure_decode container_name blob_prefix /path/to/restored_file
```

- **container_name**: Azure Blob container name.
- **blob_prefix**: Blob prefix where chunks are stored.
- **output_file**: Local file path for the decoded file.

#### Example Azure

```bash
poetry run azure_encode README.md mycontainer myblob/README_md
poetry run azure_decode mycontainer myblob/README_md ./data/README.md
```

## Build the Cython Module (Optional)

If you wish to rebuild the Cython module:

1. Navigate to the source directory:

    ```bash
    cd src/infilenamewetrust
    ```

2. Build the extension in place:

    ```bash
    python setup.py build_ext --inplace
    ```

## Fancy Ideas to Explore

- **Alternate Data Streams (ADS)**: Hide data in `filename:stream` to store "secret" streams.
- **Timestamps**: Encode small blocks of data in the creation/mod/access times.
- **Short (8.3) Names**: If 8.3 short-name generation is enabled, store data in the DOS short name.
- **Folder Names / ACLs / Reparse Points**: Exploit other NTFS features as "containers" for data.
- **Registry Keys**: Similar concept, but storing chunked data in registry subkeys or value names.
