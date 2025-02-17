from fastapi import FastAPI
from routes.players import router as players_router
from routes.groupes import router as groupes_router
from routes.tournaments import router as tournaments_router
from routes.games import router as games_router
from routes.teams import router as teams_router

app = FastAPI()
app.include_router(players_router, prefix="/players")
app.include_router(groupes_router, prefix="/groupes")
app.include_router(tournaments_router, prefix="/tournaments")
app.include_router(games_router, prefix="/games")
app.include_router(teams_router, prefix="/teams")

@app.get("/")
async def read_root():
    return {"message": "PlayerZ 🔥"}
