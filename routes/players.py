from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import database
import random
import string

router = APIRouter()

@router.get("/")
async def get_all_players(db: AsyncSession = Depends(database.get_db)):
    try:
        result = await db.execute(text("SELECT * FROM playerz.players"))
        players = result.fetchall()
        
        if not players:
            return {"message": "Aucun joueur trouvé"}
        
        columns = result.keys()
        players_list = [dict(zip(columns, player)) for player in players]
        
        return {"players": players_list}
    
    except Exception as e:
        return {"error": str(e)}

@router.get("/{id}")
async def get_player_by_id(id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        result = await db.execute(text("SELECT * FROM playerz.players WHERE id = :id"), {"id": id})
        player = result.fetchone()
        
        if player is None:
            return {"message": "Aucun joueur trouvé"}
        
        columns = result.keys()
        player_dict = dict(zip(columns, player))
        
        return {"player": player_dict}
    
    except Exception as e:
        return {"error": str(e)}

@router.post("/")
async def create_player(player_data: dict, db: AsyncSession = Depends(database.get_db)):
    try:
        query = text("INSERT INTO playerz.players (pseudo, have_avatar, avatar_url) VALUES (:pseudo, :have_avatar, :avatar_url) RETURNING id")
        result = await db.execute(query, player_data)
        new_id = result.scalar()
        await db.commit()
        
        return {"message": "Nouvel joueur ajouté avec succès", "player_data": {**player_data, "id": new_id}}
    
    except Exception as e:
        return {"error": str(e)}

@router.delete("/{id}")
async def delete_player(id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        query = text("DELETE FROM playerz.players WHERE id = :id")
        await db.execute(query, {"id": id})
        await db.commit()
        return {"message": "Joueur supprimé avec succès"}
    
    except Exception as e:
        return {"error": str(e)}

@router.put("/{id}")
async def update_player(id: int, player_data: dict, db: AsyncSession = Depends(database.get_db)):
    try:
        set_clause = ", ".join([f"{key} = :{key}" for key in player_data.keys()])
        query = text(f"UPDATE playerz.players SET {set_clause} WHERE id = :id")
        await db.execute(query, {**player_data, "id": id})
        await db.commit()
        return {"message": "Joueur mis à jour avec succès"}
    
    except Exception as e:
        return {"error": str(e)}