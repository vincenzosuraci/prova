"""Gestione delle foto profilo: validazione, ridimensionamento e salvataggio."""
import uuid
from pathlib import Path

from flask import current_app
from PIL import Image, ImageOps


def save_profile_photo(file_storage) -> str:
    """Salva la foto come JPEG quadrato e restituisce il nome del file."""
    cfg = current_app.config
    img = Image.open(file_storage.stream)
    img.verify()  # rifiuta file che non sono immagini
    file_storage.stream.seek(0)
    img = Image.open(file_storage.stream)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageOps.fit(img, cfg["PHOTO_SIZE"], Image.LANCZOS)

    filename = f"{uuid.uuid4().hex}.jpg"
    img.save(Path(cfg["UPLOAD_FOLDER"]) / filename, "JPEG", quality=88)
    return filename


def delete_profile_photo(filename):
    if filename:
        path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
        path.unlink(missing_ok=True)
