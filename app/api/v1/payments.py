from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, constr
from sqlalchemy.orm import Session
from decimal import Decimal

from app.api import deps
from app.db import models
from app.core.email import email_manager
from datetime import datetime

router = APIRouter()


class PaymentRequest(BaseModel):
    reservation_id: int
    # 9 chiffres obligatoires, côté backend aussi
    phone_number: constr(pattern=r"^\d{9}$")


@router.post("/process", status_code=status.HTTP_200_OK)
async def process_payment(
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

    # Envoi du reçu par mail
    try:
        subtotal = (reservation.vol.prix * reservation.nombre_place) if reservation.vol and reservation.nombre_place else montant
        taxes = (montant - subtotal) if subtotal < montant else Decimal("0.00")
        
        email_data = {
            "ref": f"JC-{datetime.now().year}-{reservation.id:04d}",
            "date_paiement": datetime.now().strftime("%d %B %Y").upper(),
            "client_name": current_user.nom,
            "trajet": f"{reservation.vol.ville_depart} → {reservation.vol.ville_arrivee}" if reservation.vol else "N/A",
            "seats": int(reservation.nombre_place) if reservation.nombre_place else 1,
            "depart_time": f"{reservation.vol.date_depart} {reservation.vol.heure_depart}" if reservation.vol else "N/A",
            "subtotal": f"{subtotal:.2f}",
            "taxes": f"{taxes:.2f}",
            "total": f"{montant:.2f}"
        }
        await email_manager.send_receipt(current_user.email, email_data)
    except Exception as e:
        print(f"Erreur envoi mail: {e}")
        # On ne bloque pas la réponse si le mail échoue

    return {
        "status": "payment_success",
        "reservation_id": reservation.id,
        "statut": reservation.statut,
        "montant": str(montant),
    }
