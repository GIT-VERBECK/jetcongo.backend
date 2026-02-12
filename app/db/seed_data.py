from datetime import date, time

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db import models


def seed_basic_data(db: Session) -> None:
    """
    Insère quelques avions, sièges et vols de test pour JetCongo.
    À lancer manuellement : `python -m app.db.seed_data`
    """
    # Crée quelques avions si la table est vide
    if not db.query(models.Avion).first():
        avion1 = models.Avion(
            modele="Boeing 737-800",
            capacite=180,
            statut="disponible",
            compagnie="Congo Airways",
        )
        avion2 = models.Avion(
            modele="Airbus A320",
            capacite=160,
            statut="disponible",
            compagnie="FlyCAA",
        )
        avion3 = models.Avion(
            modele="Bombardier Q400",
            capacite=78,
            statut="disponible",
            compagnie="Congo Airways",
        )
        db.add_all([avion1, avion2, avion3])
        db.commit()

    avions = db.query(models.Avion).all()
    if not avions:
        return

    avion1, avion2, avion3 = avions[:3]

    # Crée quelques vols si la table est vide
    if not db.query(models.Vol).first():
        vols = [
            models.Vol(
                ville_depart="Kinshasa",
                ville_arrivee="Goma",
                date_depart=date(2026, 3, 20),
                heure_depart=time(8, 30),
                prix=245.00,
                statut="actif",
                avion_id=avion1.id,
            ),
            models.Vol(
                ville_depart="Kinshasa",
                ville_arrivee="Goma",
                date_depart=date(2026, 3, 20),
                heure_depart=time(14, 15),
                prix=280.00,
                statut="actif",
                avion_id=avion2.id,
            ),
            models.Vol(
                ville_depart="Kinshasa",
                ville_arrivee="Goma",
                date_depart=date(2026, 3, 21),
                heure_depart=time(6, 0),
                prix=195.00,
                statut="actif",
                avion_id=avion3.id,
            ),
            models.Vol(
                ville_depart="Goma",
                ville_arrivee="Lubumbashi",
                date_depart=date(2026, 3, 20),
                heure_depart=time(9, 45),
                prix=220.00,
                statut="actif",
                avion_id=avion1.id,
            ),
        ]
        db.add_all(vols)
        db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        seed_basic_data(db)
        # Message sans emoji pour éviter les problèmes d'encodage sur certains terminaux Windows
        print("Done: Donnees de test inserees avec succes.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

