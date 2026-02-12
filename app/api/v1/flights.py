from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, selectinload
from typing import Optional
from datetime import date as date_type
from app.db import crud, schemas, models
from app.api import deps

router = APIRouter()


@router.get("/", response_model=schemas.PaginatedVolResponse)
def search_flights(
    depart: Optional[str] = Query(None),
    arrivee: Optional[str] = Query(None),
    date: Optional[date_type] = Query(None),
    sort: Optional[str] = Query("price_asc", pattern="^price_(asc|desc)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(deps.get_db),
):
    """
    Recherche de vols avec filtres dynamiques, tri et pagination.
    - depart / arrivee / date : filtrage conditionnel
    - sort : price_asc | price_desc
    - page / limit : pagination (offset = (page-1)*limit)
    """
    vols, has_more = crud.search_vols(
        db,
        depart=depart,
        arrivee=arrivee,
        date_depart=date,
        sort=sort,
        page=page,
        limit=limit,
    )

    return schemas.PaginatedVolResponse(
        data=vols,
        page=page,
        limit=limit,
        has_more=has_more,
    )


@router.get("/{vol_id}", response_model=schemas.Vol)
def get_flight(
    vol_id: int,
    db: Session = Depends(deps.get_db),
):
    """
    Récupère le détail d'un vol (incluant l'avion lié).
    Utilisé par la page de réservation pour pré-remplir le récapitulatif.
    """
    vol = (
        db.query(models.Vol)
        .options(selectinload(models.Vol.avion))
        .filter(models.Vol.id == vol_id, models.Vol.statut == "actif")
        .first()
    )

    if not vol:
        raise HTTPException(status_code=404, detail="Vol introuvable.")

    return vol
