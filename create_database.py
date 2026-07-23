import sqlite3

# Création de la base de données
conn = sqlite3.connect("lns_garage.db")

cursor = conn.cursor()

# ======================
# TABLE CLIENTS
# ======================

cursor.execute("""
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT,
    telephone TEXT,
    email TEXT,
    adresse TEXT,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ======================
# TABLE VEHICULES
# ======================

cursor.execute("""
CREATE TABLE IF NOT EXISTS vehicules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    immatriculation TEXT,
    marque TEXT,
    modele TEXT,
    annee INTEGER,
    couleur TEXT,
    kilometrage INTEGER,
    vin TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id)
)
""")

# ======================
# TABLE DEVIS
# ======================

cursor.execute("""
CREATE TABLE IF NOT EXISTS devis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    vehicule_id INTEGER,
    date_devis DATE,
    montant REAL,
    statut TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (vehicule_id) REFERENCES vehicules(id)
)
""")

conn.commit()
conn.close()

print("Base de données créée avec succès !")
