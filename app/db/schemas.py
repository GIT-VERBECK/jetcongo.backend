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


# --- Admin / Gestion Avion ---
class AvionCreate(AvionBase):
    """
    Création d'un avion dans le module d'administration.
    """
    pass


class AvionUpdate(BaseModel):
    """
    Mise à jour partielle d'un avion (admin).
    """
    modele: Optional[str] = None
    capacite: Optional[int] = None
    statut: Optional[str] = None
    compagnie: Optional[str] = None


# --- Admin / Gestion Utilisateur ---
class AdminUserUpdate(BaseModel):
    """
    Mise à jour d'un utilisateur par un administrateur.
    Permet en plus de changer le rôle et le statut métier.
    """
    email: Optional[EmailStr] = None
    nom: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


# --- Admin / Gestion Réservation ---
class AdminReservationCreate(BaseModel):
    """
    Création d'une réservation côté back-office.
    """
    utilisateur_id: int
    vol_id: int
    seats: int


class AdminReservationUpdate(BaseModel):
    """
    Mise à jour partielle d'une réservation côté back-office.
    """
    seats: Optional[int] = None
    statut: Optional[str] = None


# --- Admin / Gestion Vol ---
class VolCreate(BaseModel):
    """
    Création d'un vol côté back-office.
    """
    flight_code: str
    aircraft_id: int
    depart_city: str
    arrivee_city: str
    date_depart: date
    heure_depart: time
    price: Decimal
    status: str = "actif"


class VolUpdate(BaseModel):
    """
    Mise à jour partielle d'un vol.
    """
    flight_code: Optional[str] = None
    aircraft_id: Optional[int] = None
    depart_city: Optional[str] = None
    arrivee_city: Optional[str] = None
    date_depart: Optional[date] = None
    heure_depart: Optional[time] = None
    price: Optional[Decimal] = None
    status: Optional[str] = None

