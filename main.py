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
from routes.matches import router as matches_router
from datetime import datetime, UTC
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware



app = FastAPI()
app.include_router(players_router, prefix="/players")
app.include_router(groupes_router, prefix="/groupes")
app.include_router(tournaments_router, prefix="/tournaments")
app.include_router(games_router, prefix="/games")
app.include_router(matches_router, prefix="/matches")

app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return {"message": "PlayerZ 🔥 , by Rayan Rav & Innovita 🤖"}

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

@app.get("/file/{filename}")
async def get_file(filename: str):
    file_path = os.path.join(upload_dir, filename)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Fichier non trouvé ou chemin invalide")

    media_type, _ = mimetypes.guess_type(file_path)
    if media_type is None:
        media_type = "application/octet-stream"

    return FileResponse(file_path, media_type=media_type)