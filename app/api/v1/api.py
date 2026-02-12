from fastapi import APIRouter
from app.api.v1 import auth, users, flights, payments, reservations, admin

api_router = APIRouter()

# Auth & utilisateurs
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Vols
api_router.include_router(flights.router, prefix="/flights", tags=["flights"])

# Paiements & réservations
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(reservations.router, prefix="/reservations", tags=["reservations"])

# Tableau de bord / stats agents
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
