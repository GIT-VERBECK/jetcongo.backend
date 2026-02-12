from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date, time
from decimal import Decimal


# --- Utilisateur Schemas ---
class UtilisateurBase(BaseModel):
    email: EmailStr
    nom: str
    role: Optional[str] = "client"


class UtilisateurCreate(UtilisateurBase):
    password: str


class UtilisateurUpdate(BaseModel):
    """
    Champs modifiables par l'utilisateur dans la rubrique
    'Informations personnelles'.
    """
    email: Optional[EmailStr] = None
    nom: Optional[str] = None


class ChangePassword(BaseModel):
    """
    Payload pour le changement de mot de passe dans l'onglet Sécurité.
    """
    old_password: str
    new_password: str


class Utilisateur(UtilisateurBase):
    id: int

    class Config:
        from_attributes = True

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[int] = None

# --- Vol Schemas ---
class VolBase(BaseModel):
    ville_depart: str
    ville_arrivee: str
    date_depart: date
    heure_depart: time
    # Optionnels pour pouvoir afficher les horaires d'arrivée lorsque disponibles
    date_arrivee: Optional[date] = None
    heure_arrivee: Optional[time] = None
    prix: Decimal
    statut: str = "actif"
    avion_id: int


class AvionBase(BaseModel):
    modele: str
    capacite: int
    statut: str = "disponible"
    compagnie: Optional[str] = None


class Avion(AvionBase):
    id: int

    class Config:
        from_attributes = True


class Vol(VolBase):
    id: int
    avion: Optional[Avion] = None

    class Config:
        from_attributes = True


class PaginatedVolResponse(BaseModel):
    data: List[Vol]
    page: int
    limit: int
    has_more: bool


# --- Reservation Schemas ---
class ReservationCreate(BaseModel):
    """
    Données nécessaires pour créer une réservation côté API.
    Note : certains champs (date/heure, email) servent surtout au flux frontend
    et ne sont pas encore tous persistés dans la table Reservation.
    """
    vol_id: int
    full_name: str
    email: EmailStr
    date: date
    time: time
    seats: int = 1
