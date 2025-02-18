import os
from fastapi import UploadFile
from datetime import datetime
import aiofiles
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def upload_file_to_storage(file: UploadFile, dirr: str) -> str:
    # Utiliser le chemin configuré pour les uploads
    upload_dir = dirr
    os.makedirs(upload_dir, exist_ok=True)

    # Générer un nom de fichier unique
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    new_filename = f"{timestamp}{file_extension}"
    file_path = os.path.join(upload_dir, new_filename)
    print(file_path)

    # Sauvegarder le fichier
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    # Get URL_SERVER from environment variables
    url_server = os.getenv("URL_SERVER")

    # Retourner l'URL du fichier
    return f"{url_server}/file/{new_filename}"