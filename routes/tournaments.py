from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from sqlalchemy.engine.row import Row
import database
from datetime import datetime, timedelta

router = APIRouter()

async def row_to_dict(row):
    return dict(row._mapping)

@router.get("/")
async def get_all_tournaments(db: AsyncSession = Depends(database.get_db)):
    query = text("SELECT * FROM playerz.tournaments")
    result = await db.execute(query)
    tournaments = result.fetchall()
    tournaments_list = [row_to_dict(tournament) for tournament in tournaments]
    return {"tournaments": tournaments_list}



@router.get("/{id}")
async def get_tournament_by_id(id: int, db: AsyncSession = Depends(database.get_db)):
    query = text("SELECT * FROM playerz.tournaments where id = :id")
    result = await db.execute(query, {"id": id})
    tournament = result.fetchone()
    tournament_dict = row_to_dict(tournament) if tournament else None

    query = text("SELECT * FROM playerz.sessions where tournament_id = :id")
    result = await db.execute(query, {"id": id})
    sessions = result.fetchall()
    sessions_list = [row_to_dict(session) for session in sessions]

    query = text("SELECT * FROM playerz.matches where tournament_id = :id")
    result = await db.execute(query, {"id": id})
    matches = result.fetchall()
    matches_list = [row_to_dict(match) for match in matches]

    return {"tournament": tournament_dict, "sessions": sessions_list, "matches": matches_list}


@router.post("/")
async def create_tournament(
    tournament_data: dict, db: AsyncSession = Depends(database.get_db)
):
    try:
        # Extract and remove 'players', 'sessions', and 'matches' from tournament_data
        players = tournament_data.pop("players", [])
        sessions = tournament_data.pop("sessions", [])
        matches = tournament_data.pop("matches", [])

        # Remove duplicates from the players list
        players = list(set(players))

        # Override the 'status' column with "pas commencé"
        tournament_data["status"] = "pas commencé"

        # Insert tournament data
        keys = ", ".join(tournament_data.keys())
        values = ", ".join([f":{key}" for key in tournament_data.keys()])
        query = text(
            f"INSERT INTO playerz.tournaments ({keys}) VALUES ({values}) RETURNING id"
        )
        result = await db.execute(query, tournament_data)
        new_tournament_id = result.scalar()

        # Insert players into tournament_players table
        for player_id in players:
            player_query = text(
                "INSERT INTO playerz.tournament_players (tournament_id, player_id) VALUES (:tournament_id, :player_id)"
            )
            await db.execute(
                player_query,
                {"tournament_id": new_tournament_id, "player_id": player_id},
            )

        # Insert sessions into sessions table and collect their IDs
        session_info = []
        session_id_map = {}
        for session in sessions:
            session_query = text(
                "INSERT INTO playerz.sessions (tournament_id, reference) VALUES (:tournament_id, :reference) RETURNING id"
            )
            session_result = await db.execute(
                session_query,
                {"tournament_id": new_tournament_id, "reference": session},
            )
            session_id = session_result.scalar()
            session_info.append({"id_db": session_id, "ref": session})
            session_id_map[session] = session_id

        # Insert matches into matches table
        for match in matches:
            match["session_id"] = session_id_map.get(match["session_id"])
            match_query = text(
                "INSERT INTO playerz.matches (session_id, t1j1, t1j2, t2j1, t2j2, terrain_name) "
                "VALUES (:session_id, :t1j1, :t1j2, :t2j1, :t2j2, :terrain_name)"
            )
            await db.execute(match_query, match)

        await db.commit()
        return {"tournament_id": new_tournament_id, "sessions": session_info}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete("/{id}")
async def delete_tournament(id: int, db: AsyncSession = Depends(database.get_db)):
    try:
        query = text("DELETE FROM playerz.tournaments WHERE id = :id RETURNING *")
        result = await db.execute(query, {"id": id})
        deleted_tournament = result.fetchone()
        await db.commit()
        if deleted_tournament is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tournoi non trouvé"
            )
        return {
            "message": "Tournoi supprimé avec succès",
            "tournament": deleted_tournament,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put("/{id}")
async def update_tournament(
    id: int, tournament_data: dict, db: AsyncSession = Depends(database.get_db)
):
    try:
        set_clause = ", ".join([f"{key} = :{key}" for key in tournament_data.keys()])
        query = text(
            f"UPDATE playerz.tournaments SET {set_clause} WHERE id = :id RETURNING *"
        )
        result = await db.execute(query, {**tournament_data, "id": id})
        updated_tournament = result.fetchone()
        await db.commit()
        if updated_tournament is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tournoi non trouvé"
            )
        return updated_tournament
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
