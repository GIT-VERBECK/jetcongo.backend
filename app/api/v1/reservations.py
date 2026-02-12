from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from app.api import deps
from app.db import models, schemas

router = APIRouter()


def _compute_taken_seats(db: Session, vol_id: int) -> int:
    """
    Calcule le nombre total de places déjà réservées pour un vol donné,
    en excluant les réservations annulées.
    """
    total = (
        db.query(func.coalesce(func.sum(models.Reservation.nombre_place), 0))
        .filter(
            models.Reservation.vol_id == vol_id,
            models.Reservation.statut != "ANNULEE",
        )
        .scalar()
        or 0
    )
    return int(total)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: schemas.ReservationCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
):
    """
    Crée une réservation simple pour un vol donné, en respectant la capacité
    de l'avion associé et en calculant le total à payer.
    """
    vol = (
        db.query(models.Vol)
        .filter(models.Vol.id == payload.vol_id, models.Vol.statut == "actif")
        .first()
    )
    if not vol:
        raise HTTPException(status_code=404, detail="Vol introuvable.")

    avion = vol.avion
    if not avion or avion.capacite is None or avion.capacite <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La capacité de l'avion associé au vol est invalide.",
        )

    if payload.seats <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nombre de places doit être strictement positif.",
        )

    taken_seats = _compute_taken_seats(db, vol.id)
    remaining = avion.capacite - taken_seats

    if payload.seats > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Capacité insuffisante sur ce vol. Places restantes : {remaining}.",
        )

    # Calcul du total à payer côté backend (même logique que le frontend)
    seats = Decimal(payload.seats)
    taxe_fixe = Decimal("12.50")
    subtotal = vol.prix * seats
    total = subtotal + taxe_fixe

    reservation = models.Reservation(
        utilisateur_id=current_user.id,
        vol_id=vol.id,
        nombre_place=payload.seats,
        total_payer=total,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    return {
        "id": reservation.id,
        "statut": reservation.statut,
        "vol_id": reservation.vol_id,
        "seats": payload.seats,
        "total_payer": str(total),
    }


@router.get("/{reservation_id}", status_code=status.HTTP_200_OK)
def get_reservation(
    reservation_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
):
    """
    Récupère une réservation de l'utilisateur courant, avec les informations du vol associé.
    Utilisé par la page de paiement pour afficher le récapitulatif et le total à payer.
    """
    reservation = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.id == reservation_id,
            models.Reservation.utilisateur_id == current_user.id,
        )
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation introuvable.")

    vol = reservation.vol

    return {
        "id": reservation.id,
        "statut": reservation.statut,
        "nombre_place": int(reservation.nombre_place) if reservation.nombre_place is not None else None,
        "total_payer": str(reservation.total_payer) if reservation.total_payer is not None else None,
        "vol": {
            "id": vol.id,
            "ville_depart": vol.ville_depart,
            "ville_arrivee": vol.ville_arrivee,
            "date_depart": vol.date_depart,
            "heure_depart": str(vol.heure_depart),
            "date_arrivee": vol.date_arrivee,
            "heure_arrivee": str(vol.heure_arrivee) if vol.heure_arrivee else None,
            "prix": str(vol.prix),
        },
    }
