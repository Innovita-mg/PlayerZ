from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import database

router = APIRouter()

async def verify_players_exist(player_one: int, player_two: int, db: AsyncSession):
    query = text("SELECT id FROM playerz.players WHERE id IN (:player_one, :player_two)")
    result = await db.execute(query, {"player_one": player_one, "player_two": player_two})
    players = result.fetchall()
    if len(players) != 2:
        raise HTTPException(status_code=404, detail="One or both players not found")

@router.get("/")
async def get_all_teams(db: AsyncSession = Depends(database.get_db)):
    try:
        result = await db.execute(text("SELECT * FROM playerz.team"))
        teams = result.fetchall()
        
        if not teams:
            return {"message": "Aucune équipe trouvée"}
        
        columns = result.keys()
        teams_list = [dict(zip(columns, team)) for team in teams]
        
        return {"teams": teams_list}
    
    except Exception as e:
        return {"error": str(e)}

@router.get("/{id}")
async def get_team_by_id(id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        result = await db.execute(text("SELECT * FROM playerz.team WHERE id = :id"), {"id": id})
        team = result.fetchone()
        
        if team is None:
            return {"message": "Aucune équipe trouvée"}
        
        columns = result.keys()
        team_dict = dict(zip(columns, team))
        
        return {"team": team_dict}
    
    except Exception as e:
        return {"error": str(e)}

@router.post("/")
async def create_team(team_data: dict, db: AsyncSession = Depends(database.get_db)):
    try:
        await verify_players_exist(team_data['player_one'], team_data['player_two'], db)
        
        query = text("INSERT INTO playerz.team (tournament_id, player_one, player_two, pseudo) VALUES (:tournament_id, :player_one, :player_two, :pseudo) RETURNING id")
        result = await db.execute(query, team_data)
        new_id = result.scalar()
        await db.commit()
        
        return {"message": "Nouvelle équipe ajoutée avec succès", "team_data": {**team_data, "id": new_id}}
    
    except Exception as e:
        return {"error": str(e)}

@router.delete("/{id}")
async def delete_team(id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        query = text("DELETE FROM playerz.team WHERE id = :id")
        await db.execute(query, {"id": id})
        await db.commit()
        return {"message": "Équipe supprimée avec succès"}
    
    except Exception as e:
        return {"error": str(e)}

@router.put("/{id}")
async def update_team(id: int, team_data: dict, db: AsyncSession = Depends(database.get_db)):
    try:
        await verify_players_exist(team_data['player_one'], team_data['player_two'], db)
        
        set_clause = ", ".join([f"{key} = :{key}" for key in team_data.keys()])
        query = text(f"UPDATE playerz.team SET {set_clause} WHERE id = :id")
        await db.execute(query, {**team_data, "id": id})
        await db.commit()
        return {"message": "Équipe mise à jour avec succès"}
    
    except Exception as e:
        return {"error": str(e)} 