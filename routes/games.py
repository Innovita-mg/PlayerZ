from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from sqlalchemy.future import select
from sqlalchemy import insert, delete
from pydantic import BaseModel
from typing import List
import database

router = APIRouter()

# Define Pydantic models
class MatchCreate(BaseModel):
    date: str
    tournament_id: int
    status: str
    score_team_one: int
    score_team_two: int
    team_one: int
    team_two: int

class SessionCreate(BaseModel):
    tournament_id: int
    matches: List[MatchCreate]

class PlayerGroupAdd(BaseModel):
    player_id: int
    groupe_id: int

@router.get("/session/{id}")
async def get_all_session_of_tournament(id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        # Check if the tournament exists
        tournament_query = text("SELECT 1 FROM playerz.tournaments WHERE id = :id")
        tournament_result = await db.execute(tournament_query, {"id": id})
        tournament_exists = tournament_result.scalar()

        if not tournament_exists:
            raise HTTPException(status_code=404, detail="Tournament not found")

        # Query to get sessions and their associated matches
        query = text("""
            SELECT s.id as session_id, m.*
            FROM playerz.sessions s
            LEFT JOIN playerz.matchs m ON s.id = m.session_id
            WHERE s.tournament_id = :id
        """)
        
        result = await db.execute(query, {"id": id})
        rows = result.fetchall()
        
        if not rows:
            raise HTTPException(status_code=404, detail="No sessions found for the given tournament ID")
        
        # Organize data into a dictionary
        sessions = {}
        for row in rows:
            session_id = row['session_id']
            match_data = {key: row[key] for key in row.keys() if key != 'session_id'}
            
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(match_data)
        
        # Convert to desired output format
        session_list = [{"session_id": session_id, "matches": matches} for session_id, matches in sessions.items()]
        
        return {"sessions": session_list}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/session/create")
async def create_session_with_matches(session_data: SessionCreate, db: AsyncSession = Depends(database.get_db)):
    try:
        # Check if the tournament exists
        tournament_query = text("SELECT 1 FROM playerz.tournaments WHERE id = :id")
        tournament_result = await db.execute(tournament_query, {"id": session_data.tournament_id})
        tournament_exists = tournament_result.scalar()

        if not tournament_exists:
            raise HTTPException(status_code=404, detail="Tournament not found")

        # Insert session
        session_query = insert(database.Session).values(tournament_id=session_data.tournament_id).returning(database.Session.id)
        session_result = await db.execute(session_query)
        session_id = session_result.scalar_one()

        # Insert matches
        match_ids = []
        for match in session_data.matches:
            match_query = insert(database.Match).values(
                session_id=session_id,
                date=match.date,
                tournament_id=match.tournament_id,
                status=match.status,
                score_team_one=match.score_team_one,
                score_team_two=match.score_team_two,
                team_one=match.team_one,
                team_two=match.team_two
            ).returning(database.Match.id)
            match_result = await db.execute(match_query)
            match_ids.append(match_result.scalar_one())

        await db.commit()

        return {
            "session_id": session_id,
            "match_ids": match_ids
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/player/groupe/add")
async def add_player_to_group(data: PlayerGroupAdd, db: AsyncSession = Depends(database.get_db)):
    try:
        # Insert player into group
        query = insert(database.PlayerGroup).values(
            player_id=data.player_id,
            groupe_id=data.groupe_id
        )
        await db.execute(query)
        await db.commit()
        return {"message": "Player added to group successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/player/groupe/remove")
async def remove_player_from_group(data: PlayerGroupAdd, db: AsyncSession = Depends(database.get_db)):
    try:
        # Remove player from group
        query = delete(database.PlayerGroup).where(
            database.PlayerGroup.player_id == data.player_id,
            database.PlayerGroup.groupe_id == data.groupe_id
        )
        await db.execute(query)
        await db.commit()
        return {"message": "Player removed from group successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/player/groupe/{groupe_id}")
async def get_players_in_group(groupe_id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        # Get all players in the specified group
        query = select(database.PlayerGroup).where(database.PlayerGroup.groupe_id == groupe_id)
        result = await db.execute(query)
        players = result.fetchall()
        
        if not players:
            raise HTTPException(status_code=404, detail="No players found in the specified group")
        
        return {"players": [dict(player) for player in players]}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")