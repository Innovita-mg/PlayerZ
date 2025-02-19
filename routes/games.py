from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from sqlalchemy.future import select
from sqlalchemy import insert, delete, Column, Integer, String
from pydantic import BaseModel
from typing import List
import database
from sqlalchemy.ext.declarative import declarative_base
import random

router = APIRouter()

Base = declarative_base()

class Group(Base):
    __tablename__ = 'groupes'
    __table_args__ = {'schema': 'playerz'}
    id = Column(Integer, primary_key=True)
    # Add other fields as necessary

class GroupModel(BaseModel):
    id: int
    # Add other fields as necessary

class Player(Base):
    __tablename__ = 'players'
    __table_args__ = {'schema': 'playerz'}
    id = Column(Integer, primary_key=True)
    # Add other fields as necessary

class PlayerGroup(Base):
    __tablename__ = 'player_groupes'
    __table_args__ = {'schema': 'playerz'}
    player_id = Column(Integer, primary_key=True)
    groupe_id = Column(Integer, primary_key=True)
    # Add other fields as necessary

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

class PlayerGroupAddMultiple(BaseModel):
    player_ids: List[int]
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

@router.post("/player/groupe/add_multiple")
async def add_players_to_group(data: PlayerGroupAddMultiple, db: AsyncSession = Depends(database.get_db)):
    try:
        # Check if the group exists
        group_query = select(Group).where(Group.id == data.groupe_id)
        group_result = await db.execute(group_query)
        group_exists = group_result.scalar()

        if not group_exists:
            raise HTTPException(status_code=404, detail="GROUP NOT FOUND")

        # Insert multiple players into group
        for player_id in data.player_ids:
            # Check if the player exists
            player_query = select(Player).where(Player.id == player_id)
            player_result = await db.execute(player_query)
            player_exists = player_result.scalar()

            if not player_exists:
                raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
            
            # Insert player into group
            query = insert(PlayerGroup).values(
                player_id=player_id,
                groupe_id=data.groupe_id
            )
            await db.execute(query)
        
        # Remove duplicates
        delete_duplicates_query = text("""
            DELETE FROM playerz.player_groupes
            WHERE ctid NOT IN (
                SELECT min(ctid)
                FROM playerz.player_groupes
                GROUP BY player_id, groupe_id
            )
        """)
        await db.execute(delete_duplicates_query)

        await db.commit()
        return {"message": "SUCCESS"}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/organize_teams")
async def organize_teams(player_ids: List[int] = Body(...), is_random: bool = Body(False)):
    if len(player_ids) < 2:
        raise HTTPException(status_code=400, detail="At least two players are required to form a team.")

    # Shuffle the player IDs if is_random is True
    if is_random:
        random.shuffle(player_ids)

    # Organize players into teams of two
    teams = []
    for i in range(0, len(player_ids), 2):
        if i + 1 < len(player_ids):
            teams.append({"player1": player_ids[i], "player2": player_ids[i + 1]})
        else:
            # Handle the case where there's an odd number of players
            teams.append({"player1": player_ids[i], "player2": 0})

    return {"teams": teams}