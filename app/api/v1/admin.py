from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.api import deps
from app.db import models, schemas

router = APIRouter()


def ensure_agent(current_user: models.Utilisateur) -> models.Utilisateur:
    """
    Vérifie que l'utilisateur courant a le rôle 'agent'.
    """
    if (current_user.role or "").lower() != "agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux agents.",
        )
    return current_user


@router.get("/stats/overview")
def get_overview_stats(
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Statistiques globales pour le tableau de bord agent.
    """
    ensure_agent(current_user)

    # Vols actifs
    active_flights = db.query(func.count(models.Vol.id)).filter(models.Vol.statut == "actif").scalar() or 0

    # Réservations en attente
    pending_reservations = (
        db.query(func.count(models.Reservation.id))
        .filter(models.Reservation.statut == "EN_ATTENTE")
        .scalar()
        or 0
    )

    # Revenus totaux (tous paiements)
    total_revenue: Decimal = db.query(func.coalesce(func.sum(models.Paiement.montant), 0)).scalar() or Decimal("0.00")

    # Nombre total de passagers (somme des places réservées)
    total_passengers: Decimal = (
        db.query(func.coalesce(func.sum(models.Reservation.nombre_place), 0)).scalar() or Decimal("0")
    )

    return {
        "active_flights": int(active_flights),
        "pending_reservations": int(pending_reservations),
        "total_revenue": float(total_revenue),
        "total_passengers": int(total_passengers),
    }


@router.get("/stats/weekly-bookings")
def get_weekly_bookings(
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Nombre de réservations par jour sur les 7 derniers jours.
    """
    ensure_agent(current_user)

    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)

    # On récupère les réservations récentes et on groupe côté Python pour
    # rester compatible avec différents dialectes SQL.
    recent_reservations: List[models.Reservation] = (
        db.query(models.Reservation)
        .filter(models.Reservation.date_reservation >= seven_days_ago)
        .all()
    )

    # Dictionnaire jour anglais -> compteur
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    counts = {day: 0 for day in weekdays}

    for r in recent_reservations:
        if r.date_reservation is None:
            continue
        day_label = r.date_reservation.strftime("%a")  # Mon, Tue, ...
        if day_label in counts:
            counts[day_label] += 1

    # Retour dans l'ordre Monday -> Sunday
    data = [{"day": day, "count": counts[day]} for day in weekdays]
    return {"data": data}


@router.get("/reservations/recent")
def get_recent_reservations(
    limit: int = 5,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Dernières réservations (tous utilisateurs) pour affichage dans le tableau.
    Réservé aux agents.
    """
    ensure_agent(current_user)

    reservations = (
        db.query(models.Reservation)
        .order_by(models.Reservation.date_reservation.desc())
        .limit(limit)
        .all()
    )

    items: List[Dict[str, Any]] = []
    for r in reservations:
        user = r.utilisateur
        vol = r.vol

        passenger_name = user.nom if user else "Inconnu"
        initials = "".join([part[0] for part in passenger_name.split()[:2]]).upper() if passenger_name else "NA"

        # Code de vol synthétique : ex. GOM-KIN-012
        if vol:
            code = f"{vol.ville_depart[:3].upper()}-{vol.ville_arrivee[:3].upper()}-{r.id:03d}"
        else:
            code = f"{r.id:03d}"

        statut = r.statut or "EN_ATTENTE"
        montant = float(r.total_payer) if r.total_payer is not None else 0.0

        items.append(
            {
                "id": r.id,
                "passenger_name": passenger_name,
                "initials": initials,
                "flight_code": code,
                "status": statut,
                "amount": montant,
            }
        )

    return {"items": items}


@router.get("/flights/summary")
def get_flights_summary(
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Statistiques spécifiques aux vols pour l'écran
    d'administration "Horaires des vols".
    """
    ensure_agent(current_user)

    today = date.today()

    # Nombre total de vols prévus aujourd'hui (tous statuts confondus)
    total_flights_today = (
        db.query(func.count(models.Vol.id))
        .filter(models.Vol.date_depart == today)
        .scalar()
        or 0
    )

    # Calcul du taux de remplissage moyen sur les vols du jour
    vols_today: List[models.Vol] = (
        db.query(models.Vol)
        .options(selectinload(models.Vol.avion))
        .filter(models.Vol.date_depart == today)
        .all()
    )

    avg_load_factor = 0.0
    if vols_today:
        vol_ids = [v.id for v in vols_today]

        reservations_data = (
            db.query(
                models.Reservation.vol_id,
                func.coalesce(func.sum(models.Reservation.nombre_place), 0).label("seats_booked"),
            )
            .filter(models.Reservation.vol_id.in_(vol_ids))
            .group_by(models.Reservation.vol_id)
            .all()
        )
        seats_map = {row.vol_id: int(row.seats_booked or 0) for row in reservations_data}

        load_factors: List[float] = []
        for v in vols_today:
            capacity = (
                v.avion.capacite if v.avion is not None and v.avion.capacite is not None else 0
            )
            if capacity <= 0:
                continue
            seats_booked = seats_map.get(v.id, 0)
            load_factors.append((seats_booked / capacity) * 100.0)

        if load_factors:
            avg_load_factor = sum(load_factors) / len(load_factors)

    # Nombre de vols marqués comme annulés (tous jours confondus)
    # On tolère plusieurs libellés possibles pour le statut d'annulation.
    cancelled_statuses = ["annule", "annulé", "annulee", "annulée", "cancelled", "canceled"]
    pending_cancellations = (
        db.query(func.count(models.Vol.id))
        .filter(func.lower(models.Vol.statut).in_(cancelled_statuses))
        .scalar()
        or 0
    )

    return {
        "total_flights_today": int(total_flights_today),
        "avg_load_factor": float(round(avg_load_factor, 1)),
        "pending_cancellations": int(pending_cancellations),
    }


@router.get("/flights")
def get_admin_flights(
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Liste complète des vols pour l'interface d'administration.
    Inclut les informations d'avion et un calcul du taux de remplissage.
    """
    ensure_agent(current_user)

    query = db.query(models.Vol).options(selectinload(models.Vol.avion))
    total = query.count()

    vols: List[models.Vol] = (
        query.order_by(models.Vol.date_depart.asc(), models.Vol.heure_depart.asc())
        .limit(limit)
        .all()
    )

    vol_ids = [v.id for v in vols]
    seats_map: Dict[int, int] = {}

    if vol_ids:
        reservations_data = (
            db.query(
                models.Reservation.vol_id,
                func.coalesce(func.sum(models.Reservation.nombre_place), 0).label("seats_booked"),
            )
            .filter(models.Reservation.vol_id.in_(vol_ids))
            .group_by(models.Reservation.vol_id)
            .all()
        )
        seats_map = {row.vol_id: int(row.seats_booked or 0) for row in reservations_data}

    items: List[Dict[str, Any]] = []
    for v in vols:
        capacity = (
            v.avion.capacite if v.avion is not None and v.avion.capacite is not None else 0
        )
        seats_booked = seats_map.get(v.id, 0)
        load_factor = (seats_booked / capacity) * 100.0 if capacity > 0 else 0.0

        items.append(
            {
                "id": v.id,
                "flight_code": f"JC-{v.id:03d}",
                "depart_city": v.ville_depart,
                "arrivee_city": v.ville_arrivee,
                "date_depart": v.date_depart,
                "heure_depart": v.heure_depart,
                "date_arrivee": v.date_arrivee,
                "heure_arrivee": v.heure_arrivee,
                "price": float(v.prix),
                "status": v.statut,
                "aircraft_model": v.avion.modele if v.avion else None,
                "aircraft_capacity": capacity,
                "seats_booked": seats_booked,
                "load_factor": float(round(load_factor, 1)),
            }
        )

    return {
        "items": items,
        "total": total,
        "limit": limit,
    }


@router.post("/flights", status_code=status.HTTP_201_CREATED)
def create_flight(
    payload: schemas.VolCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Crée un nouveau vol dans le système.
    """
    ensure_agent(current_user)

    # Vérification avion
    avion = db.query(models.Avion).filter(models.Avion.id == payload.aircraft_id).first()
    if not avion:
        raise HTTPException(status_code=404, detail="Avion introuvable.")
    
    # Vérification cohérence (ex: pas de vol dans le passé ?)
    # Pour l'instant on autorise tout.

    vol = models.Vol(
        # flight_code n'est pas dans le modèle actuel (généré à la volée ou manquant ?), 
        # Le modèle Vol a: ville_depart, ville_arrivee, date_depart, heure_depart, prix, statut, avion_id
        # Le payload front envoie 'flight_code', mais le modèle DB ne l'a pas en colonne dédiée visiblement.
        # On va l'ignorer pour l'instant ou supposer qu'on utilise ID.
        # UPDATE: Le front envoie 'flight_code', mais le backend génère des faux codes 'JC-XXX'.
        # On va ignorer flight_code du payload ou le stocker si on ajoute la colonne.
        # Pour l'instant, on mappe les champs existants.
        
        ville_depart=payload.depart_city,
        ville_arrivee=payload.arrivee_city,
        date_depart=payload.date_depart,
        heure_depart=payload.heure_depart,
        prix=payload.price,
        statut=payload.status,
        avion_id=payload.aircraft_id
    )
    
    db.add(vol)
    db.commit()
    db.refresh(vol)
    
    # Relecture avec avion pour le retour
    db.refresh(vol, attribute_names=["avion"])
    
    return {
        "id": vol.id,
        "flight_code": f"JC-{vol.id:03d}",
        "depart_city": vol.ville_depart,
        "arrivee_city": vol.ville_arrivee,
        "date_depart": vol.date_depart,
        "heure_depart": vol.heure_depart,
        "price": float(vol.prix),
        "status": vol.statut,
        "aircraft_model": vol.avion.modele if vol.avion else None
    }


@router.put("/flights/{flight_id}")
def update_flight(
    flight_id: int,
    payload: schemas.VolUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Met à jour un vol existant.
    """
    ensure_agent(current_user)

    vol = db.query(models.Vol).filter(models.Vol.id == flight_id).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Vol introuvable.")

    if payload.aircraft_id is not None:
        avion = db.query(models.Avion).filter(models.Avion.id == payload.aircraft_id).first()
        if not avion:
            raise HTTPException(status_code=404, detail="Avion introuvable.")
        vol.avion_id = payload.aircraft_id

    if payload.depart_city is not None:
        vol.ville_depart = payload.depart_city
    if payload.arrivee_city is not None:
        vol.ville_arrivee = payload.arrivee_city
    if payload.date_depart is not None:
        vol.date_depart = payload.date_depart
    if payload.heure_depart is not None:
        vol.heure_depart = payload.heure_depart
    if payload.price is not None:
        vol.prix = payload.price
    if payload.status is not None:
        vol.statut = payload.status

    db.commit()
    db.refresh(vol)
    
    return {
        "id": vol.id,
        "message": "Vol mis à jour avec succès"
    }


@router.delete("/flights/{flight_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flight(
    flight_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> None:
    """
    Supprime un vol. 
    Attention: vérifier s'il a des réservations ?
    """
    ensure_agent(current_user)

    vol = db.query(models.Vol).filter(models.Vol.id == flight_id).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Vol introuvable.")

    # Vérification réservations
    has_res = db.query(models.Reservation).filter(models.Reservation.vol_id == vol.id).count()
    if has_res > 0:
         raise HTTPException(
            status_code=400, 
            detail="Impossible de supprimer ce vol car il possède des réservations. Veuillez l'annuler à la place."
        )

    db.delete(vol)
    db.commit()


# --- Gestion Avions (Fleet Management) ---
@router.get("/aircrafts")
def list_aircrafts(
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Liste les avions de la flotte avec un résumé d'utilisation.
    """
    ensure_agent(current_user)

    avions: List[models.Avion] = db.query(models.Avion).order_by(models.Avion.id.asc()).all()
    avion_ids = [a.id for a in avions]

    vols_count_map: Dict[int, int] = {}
    if avion_ids:
        rows = (
            db.query(models.Vol.avion_id, func.count(models.Vol.id))
            .filter(models.Vol.avion_id.in_(avion_ids))
            .group_by(models.Vol.avion_id)
            .all()
        )
        vols_count_map = {avion_id: int(count) for avion_id, count in rows}

    items: List[Dict[str, Any]] = []
    for a in avions:
        items.append(
            {
                "id": a.id,
                "modele": a.modele,
                "capacite": a.capacite,
                "statut": a.statut,
                "compagnie": a.compagnie,
                "vols_count": vols_count_map.get(a.id, 0),
            }
        )

    return {"items": items, "total": len(items)}


@router.post("/aircrafts", status_code=status.HTTP_201_CREATED)
def create_aircraft(
    payload: schemas.AvionCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Crée un nouvel avion dans la flotte.
    """
    ensure_agent(current_user)

    if payload.capacite <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La capacité doit être strictement positive.",
        )

    avion = models.Avion(
        modele=payload.modele,
        capacite=payload.capacite,
        statut=payload.statut,
        compagnie=payload.compagnie,
    )
    db.add(avion)
    db.commit()
    db.refresh(avion)

    return {
        "id": avion.id,
        "modele": avion.modele,
        "capacite": avion.capacite,
        "statut": avion.statut,
        "compagnie": avion.compagnie,
    }


@router.put("/aircrafts/{avion_id}")
def update_aircraft(
    avion_id: int,
    payload: schemas.AvionUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Met à jour un avion. Si son statut passe à une valeur non disponible,
    les vols actifs associés sont marqués comme bloqués.
    """
    ensure_agent(current_user)

    avion: Optional[models.Avion] = db.query(models.Avion).filter(models.Avion.id == avion_id).first()
    if not avion:
        raise HTTPException(status_code=404, detail="Avion introuvable.")

    original_status = avion.statut

    if payload.modele is not None:
        avion.modele = payload.modele
    if payload.capacite is not None:
        if payload.capacite <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La capacité doit être strictement positive.",
            )
        avion.capacite = payload.capacite
    if payload.statut is not None:
        avion.statut = payload.statut
    if payload.compagnie is not None:
        avion.compagnie = payload.compagnie

    # Si l'avion n'est plus disponible, on bloque les vols actifs associés
    if original_status != avion.statut and (avion.statut or "").lower() not in ["disponible", "available"]:
        db.query(models.Vol).filter(
            models.Vol.avion_id == avion.id,
            models.Vol.statut == "actif",
        ).update({models.Vol.statut: "bloque"}, synchronize_session=False)

    db.add(avion)
    db.commit()
    db.refresh(avion)

    return {
        "id": avion.id,
        "modele": avion.modele,
        "capacite": avion.capacite,
        "statut": avion.statut,
        "compagnie": avion.compagnie,
    }


@router.delete("/aircrafts/{avion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_aircraft(
    avion_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> None:
    """
    Supprime un avion uniquement s'il n'est utilisé par aucun vol.
    """
    ensure_agent(current_user)

    avion: Optional[models.Avion] = db.query(models.Avion).filter(models.Avion.id == avion_id).first()
    if not avion:
        raise HTTPException(status_code=404, detail="Avion introuvable.")

    used_by = db.query(models.Vol).filter(models.Vol.avion_id == avion.id).first()
    if used_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer un avion associé à au moins un vol.",
        )

    db.delete(avion)
    db.commit()


# --- Gestion Utilisateurs (back-office) ---
@router.get("/users")
def list_users(
    role: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Liste des utilisateurs avec filtres simples (rôle, statut).
    """
    ensure_agent(current_user)

    query = db.query(models.Utilisateur)
    if role:
        query = query.filter(models.Utilisateur.role == role)
    if status_filter:
        query = query.filter(models.Utilisateur.status == status_filter)

    users: List[models.Utilisateur] = query.order_by(models.Utilisateur.id.asc()).all()

    items = [
        {
            "id": u.id,
            "nom": u.nom,
            "email": u.email,
            "role": u.role,
            "status": u.status,
        }
        for u in users
    ]

    return {"items": items, "total": len(items)}


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user_admin(
    user_in: schemas.UtilisateurCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Any:
    """
    Création d'utilisateur côté back-office.
    """
    ensure_agent(current_user)

    existing = db.query(models.Utilisateur).filter(models.Utilisateur.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe déjà.",
        )

    user = models.Utilisateur(
        email=user_in.email,
        nom=user_in.nom,
        mot_de_passe="",  # défini via create_user (hash)
        role=user_in.role or "client",
    )
    # On réutilise la logique de hash via crud.create_user pour rester cohérent
    from app.db import crud

    created = crud.create_user(db, user=user_in)
    return {
        "id": created.id,
        "nom": created.nom,
        "email": created.email,
        "role": created.role,
        "status": created.status,
    }


@router.put("/users/{user_id}")
def update_user_admin(
    user_id: int,
    user_in: schemas.AdminUserUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Mise à jour d'un utilisateur par un agent/admin.
    """
    ensure_agent(current_user)

    user: Optional[models.Utilisateur] = db.query(models.Utilisateur).filter(models.Utilisateur.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    # Unicité de l'email
    if user_in.email and user_in.email != user.email:
        exists = db.query(models.Utilisateur).filter(models.Utilisateur.email == user_in.email).first()
        if exists and exists.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un utilisateur avec cet email existe déjà.",
            )
        user.email = user_in.email

    if user_in.nom is not None:
        user.nom = user_in.nom
    if user_in.role is not None:
        user.role = user_in.role
    if user_in.status is not None:
        user.status = user_in.status

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "nom": user.nom,
        "email": user.email,
        "role": user.role,
        "status": user.status,
    }


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_admin(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> None:
    """
    Supprime un utilisateur uniquement s'il n'a pas de réservations.
    """
    ensure_agent(current_user)

    user: Optional[models.Utilisateur] = db.query(models.Utilisateur).filter(models.Utilisateur.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    has_reservations = (
        db.query(models.Reservation).filter(models.Reservation.utilisateur_id == user.id).first()
        is not None
    )
    if has_reservations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer un utilisateur ayant des réservations.",
        )

    db.delete(user)
    db.commit()


# --- Gestion Réservations (back-office) ---
@router.get("/reservations")
def list_reservations_admin(
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Liste les réservations avec jointure utilisateur + vol.
    """
    ensure_agent(current_user)

    reservations: List[models.Reservation] = (
        db.query(models.Reservation)
        .options(selectinload(models.Reservation.utilisateur), selectinload(models.Reservation.vol))
        .order_by(models.Reservation.date_reservation.desc())
        .all()
    )

    items: List[Dict[str, Any]] = []
    for r in reservations:
        user = r.utilisateur
        vol = r.vol
        items.append(
            {
                "id": r.id,
                "statut": r.statut,
                "date_reservation": r.date_reservation,
                "nombre_place": int(r.nombre_place) if r.nombre_place is not None else None,
                "total_payer": float(r.total_payer) if r.total_payer is not None else None,
                "utilisateur": {
                    "id": user.id if user else None,
                    "nom": user.nom if user else None,
                    "email": user.email if user else None,
                },
                "vol": {
                    "id": vol.id if vol else None,
                    "ville_depart": vol.ville_depart if vol else None,
                    "ville_arrivee": vol.ville_arrivee if vol else None,
                    "date_depart": vol.date_depart if vol else None,
                    "heure_depart": str(vol.heure_depart) if vol and vol.heure_depart else None,
                },
            }
        )

    return {"items": items, "total": len(items)}


@router.post("/reservations", status_code=status.HTTP_201_CREATED)
def create_reservation_admin(
    payload: schemas.AdminReservationCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Création d'une réservation depuis le back-office pour un utilisateur donné.
    Respecte la capacité de l'avion et calcule le total à payer.
    """
    ensure_agent(current_user)

    user = db.query(models.Utilisateur).filter(models.Utilisateur.id == payload.utilisateur_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    vol = (
        db.query(models.Vol)
        .options(selectinload(models.Vol.avion))
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

    taken = (
        db.query(func.coalesce(func.sum(models.Reservation.nombre_place), 0))
        .filter(
            models.Reservation.vol_id == vol.id,
            models.Reservation.statut != "ANNULEE",
        )
        .scalar()
        or 0
    )
    remaining = avion.capacite - int(taken)
    if payload.seats > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Capacité insuffisante sur ce vol. Places restantes : {remaining}.",
        )

    seats_dec = Decimal(payload.seats)
    taxe_fixe = Decimal("12.50")
    subtotal = vol.prix * seats_dec
    total = subtotal + taxe_fixe

    reservation = models.Reservation(
        utilisateur_id=user.id,
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
        "nombre_place": int(reservation.nombre_place) if reservation.nombre_place is not None else None,
        "total_payer": float(total),
    }


@router.put("/reservations/{reservation_id}")
def update_reservation_admin(
    reservation_id: int,
    payload: schemas.AdminReservationUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Mise à jour de base d'une réservation (nombre de places, statut).
    """
    ensure_agent(current_user)

    reservation: Optional[models.Reservation] = (
        db.query(models.Reservation)
        .options(selectinload(models.Reservation.vol), selectinload(models.Reservation.vol, models.Vol.avion))
        .filter(models.Reservation.id == reservation_id)
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation introuvable.")

    vol = reservation.vol
    avion = vol.avion if vol else None

    if payload.seats is not None:
        if payload.seats <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nombre de places doit être strictement positif.",
            )
        if not vol or not avion or avion.capacite is None or avion.capacite <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La capacité de l'avion associé au vol est invalide.",
            )

        # recalcul de la capacité disponible en tenant compte de cette réservation
        taken = (
            db.query(func.coalesce(func.sum(models.Reservation.nombre_place), 0))
            .filter(
                models.Reservation.vol_id == vol.id,
                models.Reservation.statut != "ANNULEE",
                models.Reservation.id != reservation.id,
            )
            .scalar()
            or 0
        )
        remaining = avion.capacite - int(taken)
        if payload.seats > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Capacité insuffisante sur ce vol. Places restantes : {remaining}.",
            )

        reservation.nombre_place = payload.seats

        # Recalcule le total_payer sur la base du prix du vol
        seats_dec = Decimal(payload.seats)
        taxe_fixe = Decimal("12.50")
        subtotal = vol.prix * seats_dec
        reservation.total_payer = subtotal + taxe_fixe

    if payload.statut is not None:
        reservation.statut = payload.statut

    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    return {
        "id": reservation.id,
        "statut": reservation.statut,
        "nombre_place": int(reservation.nombre_place) if reservation.nombre_place is not None else None,
        "total_payer": float(reservation.total_payer) if reservation.total_payer is not None else None,
    }


@router.post("/reservations/{reservation_id}/confirm")
def confirm_reservation_admin(
    reservation_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Confirme une réservation (statut métier CONFIRMEE).
    """
    ensure_agent(current_user)

    reservation: Optional[models.Reservation] = db.query(models.Reservation).filter(models.Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation introuvable.")

    reservation.statut = "CONFIRMEE"
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    return {"id": reservation.id, "statut": reservation.statut}


@router.post("/reservations/{reservation_id}/cancel")
def cancel_reservation_admin(
    reservation_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.Utilisateur = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Annule une réservation (statut ANNULEE).
    """
    ensure_agent(current_user)

    reservation: Optional[models.Reservation] = db.query(models.Reservation).filter(models.Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation introuvable.")

    reservation.statut = "ANNULEE"
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    return {"id": reservation.id, "statut": reservation.statut}

