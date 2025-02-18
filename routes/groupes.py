from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import database
from routes.games import PlayerGroupAddMultiple

router = APIRouter()

async def get_players_for_groupe(groupe_id: int, db: AsyncSession):
    players_result = await db.execute(
        text("SELECT * FROM players WHERE id IN (SELECT player_id FROM player_groupes WHERE groupe_id = :id)"), 
        {"id": groupe_id}
    )
    players = players_result.fetchall()
    columns = players_result.keys()
    return [dict(zip(columns, player)) for player in players]

@router.get("/")
async def get_all_groupes(db: AsyncSession = Depends(database.get_db)):
    try:
        result = await db.execute(text("SELECT * FROM playerz.groupes"))
        groupes = result.fetchall()
        
        if not groupes:
            return {"message": "Aucun groupe trouvé"}
        
        columns = result.keys()
        groupes_list = []
        
        for groupe in groupes:
            groupe_dict = dict(zip(columns, groupe))
            groupe_dict['players'] = await get_players_for_groupe(groupe_dict['id'], db)
            groupes_list.append(groupe_dict)
        
        return {"groupes": groupes_list}
    
    except Exception as e:
        return {"error": str(e)}

@router.get("/{id}")
async def get_groupe_by_id(id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        result = await db.execute(text("SELECT * FROM playerz.groupes WHERE id = :id"), {"id": id})
        groupe = result.fetchone()
        
        if groupe is None:
            return {"message": "Aucun groupe trouvé"}
        
        columns = result.keys()
        groupe_dict = dict(zip(columns, groupe))
        groupe_dict['players'] = await get_players_for_groupe(id, db)
        
        return {"groupe": groupe_dict}
    
    except Exception as e:
        return {"error": str(e)}

@router.post("/")

async def create_groupe(groupe_data: dict, db: AsyncSession = Depends(database.get_db)):
    try:
        query = text("INSERT INTO playerz.groupes (name) VALUES (:name) RETURNING id")
        result = await db.execute(query, groupe_data)
        new_id = result.scalar()
        await db.commit()
        
        return {"message": "Nouveau groupe ajouté avec succès", "groupe_data": {**groupe_data, "id": new_id}}
    
    except Exception as e:
        return {"error": str(e)}
    

@router.delete("/{id}")
async def delete_groupe(id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        query = text("DELETE FROM playerz.groupes WHERE id = :id")
        await db.execute(query, {"id": id})
        await db.commit()
        return {"message": "Groupe supprimé avec succès"}
    
    except Exception as e:
        return {"error": str(e)}

@router.put("/{id}")
async def update_groupe(id: int, groupe_data: dict, db: AsyncSession = Depends(database.get_db)):
    try:
        set_clause = ", ".join([f"{key} = :{key}" for key in groupe_data.keys()])
        query = text(f"UPDATE playerz.groupes SET {set_clause} WHERE id = :id")
        await db.execute(query, {**groupe_data, "id": id})
        await db.commit()
        
        groupe_data['players'] = await get_players_for_groupe(id, db)
        
        return {"message": "Groupe mis à jour avec succès", "groupe_data": groupe_data}
    
    except Exception as e:
        return {"error": str(e)} 