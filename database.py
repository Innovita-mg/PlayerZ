from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration de la connexion PostgreSQL
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_USER = os.getenv("PG_USER", "playerz")
PG_PASSWORD = os.getenv("PG_PASSWORD", "playerz")
PG_DBNAME = os.getenv("PG_DBNAME", "playerz")

print("db in : ", PG_HOST)

# Création de l'engine SQLAlchemy
DATABASE_URL = f"postgresql+asyncpg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DBNAME}"
engine = create_async_engine(DATABASE_URL, echo=True)

# Création de la session
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dépendance pour obtenir une session de base de données
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
