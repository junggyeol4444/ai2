#!/usr/bin/env python3
"""
create_zip.py
Usage:
  python create_zip.py /path/to/project_folder [output_zip_name.zip]

Example:
  python create_zip.py ./auto-edit-style auto-edit-style.zip
If output filename is omitted, defaults to <foldername>.zip in current dir.
"""
import sys
from pathlib import Path
import zipfile

def zip_folder(folder: Path, out_zip: Path):
    folder = folder.resolve()
    out_zip = out_zip.resolve()
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in folder.rglob('*'):
            if p.is_file():
                # store relative path inside zip (rooted at folder)
                arcname = p.relative_to(folder)
                zf.write(p, arcname)
    return out_zip

def main():
    if len(sys.argv) < 2:
        print("Usage: python create_zip.py /path/to/project_folder [output_zip_name.zip]")
        sys.exit(1)
    folder = Path(sys.argv[1])
    if not folder.exists() or not folder.is_dir():
        print(f"Error: folder not found: {folder}")
        sys.exit(1)
    if len(sys.argv) >= 3:
        out_zip = Path(sys.argv[2])
    else:
        out_zip = Path(folder.name + ".zip")
    print(f"Creating zip {out_zip} from folder {folder} …")
    zip_path = zip_folder(folder, out_zip)
    print(f"Done. Created: {zip_path}")

if __name__ == "__main__":
    main()
