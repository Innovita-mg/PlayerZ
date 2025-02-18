import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from typing import Optional, List
from cores.storage import upload_file_to_storage
from routes.players import router as players_router
from routes.groupes import router as groupes_router
from routes.tournaments import router as tournaments_router
from routes.games import router as games_router
from routes.teams import router as teams_router
from datetime import datetime, UTC

app = FastAPI()
app.include_router(players_router, prefix="/players")
app.include_router(groupes_router, prefix="/groupes")
app.include_router(tournaments_router, prefix="/tournaments")
app.include_router(games_router, prefix="/games")
app.include_router(teams_router, prefix="/teams")

@app.get("/")
async def read_root():
    return {"message": "PlayerZ 🔥"}


# Définition du répertoire des fichiers
upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "uploads", "files"))

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