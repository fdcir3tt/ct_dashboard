import os
import requests
import zipfile

from pathlib import Path

# -----------------------------------------------------------
# SETUP
# -----------------------------------------------------------
ZIP_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/shp/gadm41_MEX_shp.zip"
DOWNLOAD_DIR = Path("data/raw")
ZIP_PATH = DOWNLOAD_DIR / "gadm41_MEX_shp.zip"
EXTRACT_DIR = DOWNLOAD_DIR / "gadm41_MEX_shp"



DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------
# DESCARGA
# -----------------------------------------------------------


with requests.get(ZIP_URL, stream=True) as r:
    r.raise_for_status()
    with open(ZIP_PATH, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

print("Download complete.")

# -----------------------------------------------------------
# DESCOMPRESIÓN
# -----------------------------------------------------------


with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
    zip_ref.extractall(EXTRACT_DIR)

print("Extraction complete.")


ZIP_PATH.unlink()
print("ZIP file deleted.")