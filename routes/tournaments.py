from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import database

router = APIRouter()

@router.get("/")
async def get_all_tournaments(db: AsyncSession = Depends(database.get_db)):
    try:
        result = await db.execute(text("SELECT * FROM playerz.tournament"))
        tournaments = result.fetchall()
        
        if not tournaments:
            return {"message": "Aucun tournoi trouvé"}
        
        columns = result.keys()
        tournaments_list = [dict(zip(columns, tournament)) for tournament in tournaments]
        
        return {"tournaments": tournaments_list}
    
    except Exception as e:
        return {"error": str(e)}

@router.get("/{id}")
async def get_tournament_by_id(id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        result = await db.execute(text("SELECT * FROM playerz.tournament WHERE id = :id"), {"id": id})
        tournament = result.fetchone()
        
        if tournament is None:
            return {"message": "Aucun tournoi trouvé"}
        
        columns = result.keys()
        tournament_dict = dict(zip(columns, tournament))
        
        return {"tournament": tournament_dict}
    
    except Exception as e:
        return {"error": str(e)}

@router.post("/")
async def create_tournament(tournament_data: dict, db: AsyncSession = Depends(database.get_db)):
    try:
        query = text("""
            INSERT INTO playerz.tournament (name, is_time_libre, time, status, place, date_deb, date_fin) 
            VALUES (:name, :is_time_libre, :time, :status, :place, :date_deb, :date_fin) 
            RETURNING id
        """)
        result = await db.execute(query, tournament_data)
        new_id = result.scalar()
        await db.commit()
        
        return {"message": "Nouveau tournoi ajouté avec succès", "tournament_data": {**tournament_data, "id": new_id}}
    
    except Exception as e:
        return {"error": str(e)}

@router.delete("/{id}")
async def delete_tournament(id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        query = text("DELETE FROM playerz.tournament WHERE id = :id")
        await db.execute(query, {"id": id})
        await db.commit()
        return {"message": "Tournoi supprimé avec succès"}
    
    except Exception as e:
        return {"error": str(e)}

@router.put("/{id}")
async def update_tournament(id: int, tournament_data: dict, db: AsyncSession = Depends(database.get_db)):
    try:
        set_clause = ", ".join([f"{key} = :{key}" for key in tournament_data.keys()])
        query = text(f"UPDATE playerz.tournament SET {set_clause} WHERE id = :id")
        await db.execute(query, {**tournament_data, "id": id})
        await db.commit()
        return {"message": "Tournoi mis à jour avec succès"}
    
    except Exception as e:
        return {"error": str(e)} 