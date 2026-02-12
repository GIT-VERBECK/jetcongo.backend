from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Time, ForeignKey, Numeric, CheckConstraint, text, Index, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Utilisateur(Base):
    __tablename__ = "utilisateur"
    
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    mot_de_passe = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="client") # 'client' ou 'admin'
    # Statut métier de l'utilisateur (ACTIVE, SUSPENDED, etc.)
    status = Column(String(50), nullable=True)
    # Avatar binaire et type MIME optionnels
    avatar = Column(LargeBinary, nullable=True)
    avatar_mime = Column(String(50), nullable=True)

class Avion(Base):
    __tablename__ = "avion"
    
    id = Column(Integer, primary_key=True, index=True)
    modele = Column(String(100), nullable=False)
    capacite = Column(Integer, nullable=False)
    # Nom de la compagnie aérienne, par ex. "Congo Airways"
    compagnie = Column(String(100), nullable=True)
    statut = Column(String(20), nullable=False, server_default="disponible")

    __table_args__ = (CheckConstraint('capacite > 0'),)

class Vol(Base):
    __tablename__ = "vol"
    
    id = Column(Integer, primary_key=True, index=True)
    ville_depart = Column(String(100), nullable=False)
    ville_arrivee = Column(String(100), nullable=False)
    date_depart = Column(Date, nullable=False)
    heure_depart = Column(Time, nullable=False)
    # Optionnels pour l'instant : permettent d'afficher les horaires d'arrivée
    date_arrivee = Column(Date, nullable=True)
    heure_arrivee = Column(Time, nullable=True)
    prix = Column(Numeric(10, 2), nullable=False)
    statut = Column(String(20), nullable=False, server_default="actif")
    avion_id = Column(Integer, ForeignKey("avion.id", ondelete="CASCADE"), nullable=False)

    avion = relationship("Avion")
    __table_args__ = (
        CheckConstraint('prix >= 0'),
        # Indexes pour optimiser la recherche et le tri
        Index("idx_vol_ville_depart", "ville_depart"),
        Index("idx_vol_ville_arrivee", "ville_arrivee"),
        Index("idx_vol_date_depart", "date_depart"),
        Index("idx_vol_prix", "prix"),
        Index("idx_vol_statut", "statut"),
        Index("idx_vol_avion_id", "avion_id"),
    )

class Reservation(Base):
    __tablename__ = "reservation"
    
    id = Column(Integer, primary_key=True, index=True)
    date_reservation = Column(DateTime, server_default=func.now())
    statut = Column(String(20), nullable=False, server_default="EN_ATTENTE")
    utilisateur_id = Column(Integer, ForeignKey("utilisateur.id", ondelete="CASCADE"), nullable=False)
    vol_id = Column(Integer, ForeignKey("vol.id", ondelete="CASCADE"), nullable=False)
    # Nombre de places réservées pour ce vol
    nombre_place = Column(Numeric(10, 0), nullable=True)
    # Montant total payé (prix * nombre_place + taxes/frais)
    total_payer = Column(Numeric(10, 2), nullable=True)
    
    utilisateur = relationship("Utilisateur")
    vol = relationship("Vol")

class ModePaiement(Base):
    __tablename__ = "modepaiement"
    
    id = Column(Integer, primary_key=True, index=True)
    libelle = Column(String(50), unique=True, nullable=False)

class Paiement(Base):
    __tablename__ = "paiement"
    
    id = Column(Integer, primary_key=True, index=True)
    montant = Column(Numeric(10, 2), nullable=False)
    date_paiement = Column(DateTime, server_default=func.now())
    reservation_id = Column(Integer, ForeignKey("reservation.id", ondelete="CASCADE"), unique=True)
    mode_paiement_id = Column(Integer, ForeignKey("modepaiement.id", ondelete="RESTRICT"), nullable=False)
    # Numéro Mobile Money utilisé pour le paiement (sans indicatif)
    phone_number = Column(String(20), nullable=True)

    reservation = relationship("Reservation")
    mode_paiement = relationship("ModePaiement")
    __table_args__ = (CheckConstraint('montant >= 0'),)
