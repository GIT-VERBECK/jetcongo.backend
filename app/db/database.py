from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

"""
Configuration centrale de la connexion à la base PostgreSQL.
Compatible local/Docker, Supabase et Render, en respectant :
- URL unique dans la variable d'environnement DATABASE_URL
- Connexion SSL obligatoire pour Supabase
- Pool de connexion robuste (pool_pre_ping)
"""

db_url = settings.DATABASE_URL

# Forcer sslmode=require si l'on détecte un host Supabase et qu'aucun sslmode
# n'est déjà présent dans l'URL. Cela évite les erreurs de connexion TLS.
connect_args = {}
if "supabase.co" in db_url and "sslmode=" not in db_url:
    connect_args["sslmode"] = "require"

engine = create_engine(
    db_url,
    pool_pre_ping=True,  # Vérifie les connexions avant réutilisation
    pool_size=5,
    max_overflow=10,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    Dépendance FastAPI pour obtenir une session SQLAlchemy.
    À utiliser avec Depends(get_db) dans les routes / services.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
