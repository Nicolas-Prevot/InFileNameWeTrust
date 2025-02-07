# InFileNameWeTrust

**InFileNameWeTrust** is a whimsical experiment that stores entire file contents in the filenames themselves—the ultimate proof-of-concept for “hidden” storage via filename abuse on Windows.

Each file is **0 bytes**, yet it secretly embeds all your data in its name. It’s silly, it’s impractical, but it works—and that’s precisely why we love it.

No disclaimers—just pure madness. InFileNameWeTrust!

## How It Works

1. **Compression**  
   We first compress the input file with zlib to make it smaller and more uniform.

2. **Base-N Encoding**  
   We interpret the compressed bytes as a large integer and convert it into base **N**, where **N** can be ~63,000–65,000. Our “digits” are **valid Unicode BMP characters** that Windows allows in filenames.

3. **Chunking**  
   Windows imposes a limit on filename length (usually 255 UTF-16 code units, or more with “long path” support). We split the encoded string into chunks short enough to fit within that limit. Each chunk becomes a **zero-byte file** named like: `000000__<chunk> 000001__<chunk> ...`

4. **Decoding**
    - We sort the files by numeric index (the `000000` part).  
    - We concatenate all the chunks from the filenames.  
    - We decode from base-N back to bytes.  
    - We decompress with zlib, restoring the original file data.

### Why Zero-Byte?

Because **all** the data lives in the filenames, the file contents are empty. Yet collectively, these “empty” files reconstruct your original data. Only with Windows.

## Installation and Usage

1. Clone the Repository

    ```bash
    git clone https://github.com/Nicolas-Prevot/InFileNameWeTrust.git
    cd InFileNameWeTrust
    ```

2. Start by instanciating your *Conda* environment (or favorite environment setup) by running the following command:

    ```bash
    conda env create -v -f environment.yml
    conda activate infilenamewetrust
    ```

3. Install project dependencies with *Poetry*:

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

### Decoding

```bash
poetry run decode /path/to/output_dir /path/to/restored_file
```

- **output_dir**: The directory containing the chunk files.
- **restored_file**: Where to write the reconstructed data.

### Example

```bash
poetry run encode README.md ./data
poetry run decode ./data/README_md ./data/README.md
```

## Fancy Ideas to Explore

- **Alternate Data Streams (ADS)**: Hide data in `filename:stream` to store “secret” streams.
- **Timestamps**: Encode small blocks of data in the creation/mod/access times.
Short (8.3) Names: If 8.3 short-name generation is enabled, store data in the DOS short name.
- **Folder Names / ACLs / Reparse Points**: Exploit other NTFS features as “containers” for data.
- **Registry Keys**: Similar concept, but storing chunked data in registry subkeys or value names.
