import mimetypes
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from typing import Optional, List

from fastapi.responses import FileResponse
from cores.storage import upload_file_to_storage
from routes.players import router as players_router
from routes.groupes import router as groupes_router
from routes.tournaments import router as tournaments_router
from routes.games import router as games_router
from routes.teams import router as teams_router
from datetime import datetime, UTC
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.include_router(players_router, prefix="/players")
app.include_router(groupes_router, prefix="/groupes")
app.include_router(tournaments_router, prefix="/tournaments")
app.include_router(games_router, prefix="/games")
app.include_router(teams_router, prefix="/teams")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to the specific origins you want to allow
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_request_origin_and_ip(request: Request, call_next):
    origin = request.headers.get("origin")
    client_ip = request.client.host
    # print(f"YO : Request Origin: {origin}, Client IP: {client_ip}")
    print("--------------------------------")
    print(request)
    print("--------------------------------")
    response = await call_next(request)
    return response

@app.get("/")
async def read_root():
    return {"message": "PlayerZ 🔥"}


# Définition du répertoire des fichiers
upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "files"))

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    
    allowed_types = ["image/jpeg", "image/png"]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="FORMAT NOT SUPPORTED"
        )

    try:
        file_url = await upload_file_to_storage(file, upload_dir)
        return {"message": "SUCCESS", "file_url": file_url}
       
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'upload du média: {str(e)}"
        )

@app.get("/file/{filename}")  # Utilisation d'un paramètre dans l'URL
async def get_file(filename: str):
    # Endpoint pour afficher un fichier dans le navigateur
    file_path = os.path.join(upload_dir, filename)
    
    print(file_path)

    # Vérifier si le fichier existe et que ce n'est pas un dossier
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Fichier non trouvé ou chemin invalide")

    # Détecter le type de fichier
    media_type, _ = mimetypes.guess_type(file_path)
    if media_type is None:
        media_type = "application/octet-stream"  # Type par défaut si inconnu

    return FileResponse(file_path, media_type=media_type)