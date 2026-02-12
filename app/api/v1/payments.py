from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, constr
from sqlalchemy.orm import Session
from decimal import Decimal

from app.api import deps
from app.db import models

router = APIRouter()


class PaymentRequest(BaseModel):
    reservation_id: int
    # 9 chiffres obligatoires, côté backend aussi
    phone_number: constr(pattern=r"^\d{9}$")


@router.post("/process", status_code=status.HTTP_200_OK)
def process_payment(
    payload: PaymentRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
):
    """
    Traite un paiement Mobile Money :
    - vérifie que la réservation appartient à l'utilisateur courant
    - empêche le double paiement
    - enregistre un paiement en base
    - met à jour le statut de la réservation en 'PAYE'
    """
    reservation = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.id == payload.reservation_id,
            models.Reservation.utilisateur_id == current_user.id,
        )
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation introuvable.")

    # Vérifie si un paiement existe déjà pour cette réservation
    existing_payment = (
        db.query(models.Paiement)
        .filter(models.Paiement.reservation_id == reservation.id)
        .first()
    )
    if existing_payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le paiement pour cette réservation a déjà été effectué.",
        )

    # Trouve ou crée le mode de paiement "Mobile Money"
    mode = (
        db.query(models.ModePaiement)
        .filter(models.ModePaiement.libelle == "Mobile Money")
        .first()
    )
    if not mode:
        mode = models.ModePaiement(libelle="Mobile Money")
        db.add(mode)
        db.commit()
        db.refresh(mode)

    montant = reservation.total_payer or Decimal("0.00")

    paiement = models.Paiement(
        montant=montant,
        reservation_id=reservation.id,
        mode_paiement_id=mode.id,
        phone_number=payload.phone_number,
    )
    db.add(paiement)

    reservation.statut = "PAYE"
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    return {
        "status": "payment_success",
        "reservation_id": reservation.id,
        "statut": reservation.statut,
        "montant": str(montant),
    }
