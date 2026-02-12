-- Indexes pour optimiser les recherches de vols

CREATE INDEX IF NOT EXISTS idx_vol_ville_depart ON vol(ville_depart);
CREATE INDEX IF NOT EXISTS idx_vol_ville_arrivee ON vol(ville_arrivee);
CREATE INDEX IF NOT EXISTS idx_vol_date_depart ON vol(date_depart);
CREATE INDEX IF NOT EXISTS idx_vol_prix ON vol(prix);
CREATE INDEX IF NOT EXISTS idx_vol_statut ON vol(statut);

