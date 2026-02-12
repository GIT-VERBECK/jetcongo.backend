from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from app.db.database import engine, Base

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


@app.on_event("startup")
def on_startup() -> None:
    """
    S'assure que toutes les tables définies dans les modèles SQLAlchemy
    existent dans la base pointée par DATABASE_URL.
    Si tu as déjà créé les tables dans *cette* base Supabase,
    cette commande est idempotente et ne les recréera pas.
    """
    Base.metadata.create_all(bind=engine)


# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to JetCongo API", "docs": "/docs"}
