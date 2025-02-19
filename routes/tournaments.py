from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import database

router = APIRouter()

async def enrich_tournament_data(tournament_id: int, db: AsyncSession):
    # Fetch tournament data
    tournament_query = text("SELECT * FROM playerz.tournament WHERE id = :id")
    result = await db.execute(tournament_query, {"id": tournament_id})
    tournament_data = result.fetchone()
    if not tournament_data:
        return None

    # Convert tournament_data to a dictionary using result.keys()
    columns = result.keys()
    tournament_data = dict(zip(columns, tournament_data))

    # Fetch player IDs from tournament_players table
    player_query = text("SELECT player_id FROM playerz.tournament_players WHERE tournament_id = :tournament_id")
    result = await db.execute(player_query, {"tournament_id": tournament_id})
    player_ids = [row.player_id for row in result.fetchall()]

    # Enrich players
    players_doc = []
    for player_id in player_ids:
        player_query = text("SELECT * FROM playerz.players WHERE id = :id")
        result = await db.execute(player_query, {"id": player_id})
        player_doc = result.fetchone()
        if player_doc:
            player_columns = result.keys()
            players_doc.append(dict(zip(player_columns, player_doc)))
    tournament_data["players_doc"] = players_doc

    # Fetch and enrich teams
    team_query = text("SELECT * FROM playerz.team WHERE tournament_id = :tournament_id")
    result = await db.execute(team_query, {"tournament_id": tournament_id})
    teams = []
    for row in result.fetchall():
        team = dict(zip(result.keys(), row))
        
        # Enrich player_one
        player_one_query = text("SELECT * FROM playerz.players WHERE id = :id")
        result_one = await db.execute(player_one_query, {"id": team["player_one"]})
        player_one_doc = result_one.fetchone()
        if player_one_doc:
            player_one_columns = result_one.keys()
            team["player_one_doc"] = dict(zip(player_one_columns, player_one_doc))
        
        # Enrich player_two
        player_two_query = text("SELECT * FROM playerz.players WHERE id = :id")
        result_two = await db.execute(player_two_query, {"id": team["player_two"]})
        player_two_doc = result_two.fetchone()
        if player_two_doc:
            player_two_columns = result_two.keys()
            team["player_two_doc"] = dict(zip(player_two_columns, player_two_doc))
        
        teams.append(team)
    
    tournament_data["teams"] = teams

    # Fetch and enrich sessions
    session_query = text("SELECT * FROM playerz.sessions WHERE tournament_id = :tournament_id")
    result = await db.execute(session_query, {"tournament_id": tournament_id})
    sessions = []
    for session_row in result.fetchall():
        session = dict(zip(result.keys(), session_row))
        
        # Fetch matches for each session
        match_query = text("SELECT * FROM playerz.matchs WHERE session_id = :session_id")
        match_result = await db.execute(match_query, {"session_id": session["id"]})
        matches = [dict(zip(match_result.keys(), match_row)) for match_row in match_result.fetchall()]
        
        session["matchs"] = matches
        sessions.append(session)
    
    tournament_data["sessions"] = sessions

    return tournament_data

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
        # result = await db.execute(text("SELECT * FROM playerz.tournament WHERE id = :id"), {"id": id})
        # tournament = result.fetchone()
        # if tournament is None:
        #     return {"message": "Aucun tournoi trouvé"}
        # # Use result.keys() to map the row to a dictionary
        # columns = result.keys()
        # tournament_dict = dict(zip(columns, tournament))
        # return {"tournament": tournament_dict}
    
        # Enrich tournament data
        enriched_data = await enrich_tournament_data(id, db)
        return enriched_data

    
    except Exception as e:
        return {"error": str(e)}

@router.post("/")
async def create_tournament(tournament_data: dict, db: AsyncSession = Depends(database.get_db)):
    try:
        # Insert tournament data
        tournament_query = text("""
            INSERT INTO playerz.tournament (name, is_time_libre, time, status, place) 
            VALUES (:name, :is_time_libre, :time, :status, :place) 
            RETURNING id
        """)
        result = await db.execute(tournament_query, tournament_data)
        new_tournament_id = result.scalar()

        # Insert players
        player_ids = tournament_data.get("players", [])
        for player_id in player_ids:
            player_query = text("""
                INSERT INTO playerz.tournament_players (tournament_id, player_id) 
                VALUES (:tournament_id, :player_id)
            """)
            await db.execute(player_query, {"tournament_id": new_tournament_id, "player_id": player_id})

        # Insert teams
        teams = tournament_data.get("teams", [])
        for team in teams:
            team_query = text("""
                INSERT INTO playerz.team (tournament_id, player_one, player_two, code) 
                VALUES (:tournament_id, :player_one, :player_two, :code)
            """)
            await db.execute(team_query, {"tournament_id": new_tournament_id, **team})

        # Insert sessions
        sessions = tournament_data.get("sessions", [])
        for session in sessions:
            session_query = text("""
                INSERT INTO playerz.sessions (tournament_id) 
                VALUES (:tournament_id) 
                RETURNING id
            """)
            session_result = await db.execute(session_query, {"tournament_id": new_tournament_id})
            new_session_id = session_result.scalar()

            # Insert matches for each session
            matches = session.get("matchs", [])
            for match in matches:
                match_query = text("""
                    INSERT INTO playerz.matchs (session_id, team_one, team_two) 
                    VALUES (:session_id, :team_one, :team_two)
                """)
                await db.execute(match_query, {"session_id": new_session_id, **match})

        await db.commit()

        # Enrich tournament data
        enriched_data = await enrich_tournament_data(new_tournament_id, db)

        return {"message": "SUCCESS", "tournament_data": enriched_data}

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