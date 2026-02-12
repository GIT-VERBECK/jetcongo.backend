from sqlalchemy.orm import Session, selectinload
from datetime import date as date_type
from typing import Optional, Tuple, List
from app.db import models, schemas
from app.core.security import get_password_hash
from fastapi import HTTPException

# --- Utilisateur ---
def get_user_by_email(db: Session, email: str):
    try:
        return db.query(models.Utilisateur).filter(models.Utilisateur.email == email).first()
    except Exception as e:
        print(f"Erreur DB recherche: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur DB: {str(e)}")

def create_user(db: Session, user: schemas.UtilisateurCreate):
    try:
        hashed_password = get_password_hash(user.password)
        db_user = models.Utilisateur(
            email=user.email,
            mot_de_passe=hashed_password,
            nom=user.nom,
            role=user.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        print(f"Erreur DB création: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion DB: {str(e)}")


# --- Vol ---
def get_vols(db: Session, skip: int = 0, limit: int = 100) -> List[models.Vol]:
    return db.query(models.Vol).offset(skip).limit(limit).all()


def search_vols(
    db: Session,
    *,
    depart: Optional[str] = None,
    arrivee: Optional[str] = None,
    date_depart: Optional[date_type] = None,
    sort: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
) -> Tuple[List[models.Vol], bool]:
    """
    Recherche avancée de vols avec filtres dynamiques, tri et pagination.
    Retourne (vols, has_more).
    """
    query = (
        db.query(models.Vol)
        .options(selectinload(models.Vol.avion))
        .filter(models.Vol.statut == "actif")
    )

    if depart:
        query = query.filter(models.Vol.ville_depart == depart)
    if arrivee:
        query = query.filter(models.Vol.ville_arrivee == arrivee)
    if date_depart is not None:
        query = query.filter(models.Vol.date_depart == date_depart)

    # Tri dynamique
    if sort == "price_desc":
        query = query.order_by(models.Vol.prix.desc())
    else:
        # Par défaut ou "price_asc"
        query = query.order_by(models.Vol.prix.asc())

    # Pagination
    offset = (page - 1) * limit
    results = query.limit(limit).offset(offset).all()
    has_more = len(results) == limit

    return results, has_more
