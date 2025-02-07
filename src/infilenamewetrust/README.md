
## Encode

```bash
python ifnwt_manager.py encode mydata.bin out_folder --segment_size=100000 --chunk_size=240
```

```bash
python ifnwt_manager.py encode C:\Users\Utilisateur\Downloads\PXL_20230907_044910318.jpg ../data --segment_size=100000 --chunk_size=100
```

## Decode

```bash
python ifnwt_manager.py decode out_folder/mydata_bin restored_mydata.bin
```