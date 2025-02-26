from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from sqlalchemy.engine.row import Row
import database
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/")
async def get_all_tournaments(db: AsyncSession = Depends(database.get_db)):
    query = text(
        """
        SELECT *,
            (select count(*) from playerz.tournament_players where tournament_id = t.id) 
            as nb_joueurs 
        FROM playerz.tournaments t 
        ORDER BY id DESC
    """
    )
    result = await db.execute(query)
    tournaments = result.fetchall()

    if not tournaments:
        return {"message": "TOURNAMENTS_NOT_FOUND", "tournaments": []}

    columns = result.keys()
    tournaments_list = [dict(zip(columns, tournament)) for tournament in tournaments]
    return {"message": "SUCCES", "tournaments": tournaments_list}


@router.get("/{id}/ranking")
async def get_tournament_ranking(id: int, db: AsyncSession = Depends(database.get_db)):
    query = text(
        """
        SELECT * FROM get_tournament_ranking(:id);
        """
    )
    result = await db.execute(query, {"id": id})
    ranking = result.fetchall()
    columns = result.keys()
    ranking_list = [dict(zip(columns, ranking)) for ranking in ranking]
    return {"message": "SUCCES", "ranking": ranking_list}


@router.get("/sessions/{id}/in-tournament")
async def get_session_by_id_tournament(
    id: int, db: AsyncSession = Depends(database.get_db)
):
    query = text(
        """
        SELECT 
        ROW_NUMBER() OVER (ORDER BY id) AS num, 
        id 
        FROM sessions 
        WHERE tournament_id = :id;
        """
    )
    result = await db.execute(query, {"id": id})
    sessions = result.fetchall()
    if not sessions:
        return {"message": "SESSIONS_NOT_FOUND", "sessions": []}
    columns = result.keys()
    sessions_list = [dict(zip(columns, session)) for session in sessions]
    return {"message": "SUCCESS", "sessions": sessions_list}


@router.get("/{id}")
async def get_tournament_by_id(id: int, db: AsyncSession = Depends(database.get_db)):

    query = text(
        """
        SELECT *,
            (select count(*) from playerz.tournament_players where tournament_id = t.id) 
            as nb_joueurs 
        FROM playerz.tournaments t 
        WHERE t.id = :id
    """
    )
    result = await db.execute(query, {"id": id})
    tournament = result.fetchone()

    if not tournament:
        return {
            "message": "TOURNAMENT_NOT_FOUND",
            "tournament": {},
            "sessions": [],
            "matches": [],
            "players": [],
        }

    columns = result.keys()
    tournament_dict = dict(zip(columns, tournament))

    query = text(
        """
        SELECT * FROM playerz.players WHERE id IN (
            SELECT player_id FROM playerz.tournament_players WHERE tournament_id = :id
        )
        """
    )
    result = await db.execute(query, {"id": id})
    players = result.fetchall()

    columns = result.keys()
    players_list = [dict(zip(columns, player)) for player in players]

    query = text("SELECT * FROM playerz.sessions WHERE tournament_id = :id")
    result = await db.execute(query, {"id": id})
    sessions = result.fetchall()

    if not sessions:
        return {
            "message": "SUCCES",
            "tournament": tournament_dict,
            "sessions": [],
            "matches": [],
            "players": players_list,
        }

    columns = result.keys()
    sessions_list = [dict(zip(columns, session)) for session in sessions]

    query = text(
        "SELECT * FROM playerz.matches WHERE session_id IN (SELECT id FROM playerz.sessions WHERE tournament_id = :id)"
    )
    result = await db.execute(query, {"id": id})
    matches = result.fetchall()

    if not matches:
        return {
            "message": "SUCCES",
            "tournament": tournament_dict,
            "sessions": sessions_list,
            "matches": [],
            "players": players_list,
        }

    columns = result.keys()
    matches_list = [dict(zip(columns, match)) for match in matches]

    return {
        "message": "SUCCES",
        "tournament": tournament_dict,
        "sessions": sessions_list,
        "matches": matches_list,
        "players": players_list,
    }


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
        tournament_data["status"] = "Non commencé"

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
            match["status"] = "Non commencé"
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
                status_code=status.HTTP_404_NOT_FOUND, detail="TOURNAMENT_NOT_FOUND"
            )
        columns = result.keys()
        tournament_dict = dict(zip(columns, deleted_tournament))
        return {"message": "TOURNAMENT_DELETED", "tournament": tournament_dict}
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
                status_code=status.HTTP_404_NOT_FOUND, detail="TOURNAMENT_NOT_FOUND"
            )
        columns = result.keys()
        tournament_dict = dict(zip(columns, updated_tournament))
        return {"message": "TOURNAMENT_UPDATED", "tournament": tournament_dict}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
